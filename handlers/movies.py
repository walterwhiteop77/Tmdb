import re
import asyncio
import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction

from config.database import get_user_config
from config.settings import SETTINGS
from services.tmdb_api import tmdb_service
from services.imdb_scraper import imdb_scraper
from services.poster_generator import poster_generator
from utils.helpers import parse_query, extract_season_episode

logger = logging.getLogger(__name__)

async def handle_movie_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle movie/TV show requests."""
    user = update.effective_user
    
    # Check if user is admin
    if user.id != SETTINGS.ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ This bot is restricted to admin use only."
        )
        return
    
    query = update.message.text.strip()
    
    if not query:
        return
    
    # Send typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    try:
        # Parse the query
        title, year, season, episode = parse_query(query)
        
        if not title:
            await update.message.reply_text(
                "❌ Could not parse the title from your request.\n\n"
                "Please try formats like:\n"
                "• `Movie Title`\n"
                "• `Movie Title 2023`\n"
                "• `TV Show S01E01`\n"
                "• `TV Show Season 1 Episode 1`"
            )
            return
        
        logger.info(f"Parsed query - Title: {title}, Year: {year}, Season: {season}, Episode: {episode}")
        
        # Show searching message
        search_msg = await update.message.reply_text(
            f"🔍 Searching for **{title}**{f' ({year})' if year else ''}...",
            parse_mode='Markdown'
        )
        
        # Try TMDB first with detailed logging
        movie_data = None
        source = None
        
        try:
            logger.info(f"Starting TMDB search for: {title}")
            if season or episode:
                logger.info("Searching as TV show")
                movie_data = await tmdb_service.search_tv(title, year)
            else:
                logger.info("Searching as movie")
                movie_data = await tmdb_service.search_movie(title, year)
            
            if movie_data:
                source = "TMDB"
                logger.info(f"TMDB search successful: {movie_data.get('title')}")
            else:
                logger.warning("TMDB search returned no data")
                
        except Exception as e:
            logger.error(f"TMDB search failed with exception: {e}", exc_info=True)
            await search_msg.edit_text(
                f"🔍 TMDB error, trying IMDb for **{title}**...",
                parse_mode='Markdown'
            )
        
        # If TMDB failed, try IMDb
        if not movie_data:
            try:
                logger.info(f"Starting IMDb search for: {title}")
                await search_msg.edit_text(
                    f"🔍 TMDB failed, trying IMDb for **{title}**...",
                    parse_mode='Markdown'
                )
                
                movie_data = await imdb_scraper.search_and_get_details(title, year)
                if movie_data:
                    source = "IMDb"
                    logger.info(f"IMDb search successful: {movie_data.get('title')}")
                else:
                    logger.warning("IMDb search returned no data")
                    
            except Exception as e:
                logger.error(f"IMDb search failed with exception: {e}", exc_info=True)
        
        if not movie_data:
            logger.error(f"Both TMDB and IMDb searches failed for: {title}")
            await search_msg.edit_text(
                f"❌ Sorry, I couldn't find **{title}**{f' ({year})' if year else ''} on either TMDB or IMDb.\n\n"
                f"Please check the spelling or try a different format.\n\n"
                f"**Debug info:** Check Render logs for detailed errors.",
                parse_mode='Markdown'
            )
            return
        
        logger.info(f"Movie data found from {source}: {movie_data.get('title')}")
        
        # For now, just send the movie details without generating poster
        # This helps us confirm the search is working
        details_text = f"""
✅ **Found on {source}!**

🎬 **{movie_data.get('title', 'N/A')}**
📅 **Year:** {movie_data.get('year', 'N/A')}
⭐ **Rating:** {movie_data.get('rating', 'N/A')}/10
🌐 **Language:** {movie_data.get('language', 'N/A')}
🎭 **Genre:** {movie_data.get('genres', 'N/A')}
👨‍🎬 **Director:** {movie_data.get('director', 'N/A')}
📝 **Plot:** {movie_data.get('plot', 'N/A')[:200]}...

_Poster generation temporarily disabled for testing._
        """
        
        await search_msg.edit_text(details_text, parse_mode='Markdown')
        
        logger.info(f"Successfully processed request for {title}")
        
    except Exception as e:
        logger.error(f"Error in handle_movie_request: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ An error occurred while processing your request:\n`{str(e)[:100]}`\n\nCheck Render logs for details.",
            parse_mode='Markdown'
        )

def _format_movie_details(movie_data: dict, source: str) -> str:
    """Format movie data for caption."""
    details = [
        f"🎬 **{movie_data.get('title', 'N/A')}**",
    ]
    
    if movie_data.get('year') and movie_data['year'] != 'N/A':
        details.append(f"📅 **Year:** {movie_data['year']}")
    
    if movie_data.get('rating') and movie_data['rating'] != 'N/A':
        details.append(f"⭐ **Rating:** {movie_data['rating']}/10")
    
    if movie_data.get('language') and movie_data['language'] != 'N/A':
        details.append(f"🌐 **Language:** {movie_data['language']}")
    
    if movie_data.get('genres') and movie_data['genres'] != 'N/A':
        details.append(f"🎭 **Genre:** {movie_data['genres']}")
    
    if movie_data.get('director') and movie_data['director'] != 'N/A':
        details.append(f"👨‍🎬 **Director:** {movie_data['director']}")
    
    # Add season/episode info for TV shows
    if movie_data.get('season') and movie_data.get('episode'):
        details.append(f"📺 **S{movie_data['season']:02d}E{movie_data['episode']:02d}**")
    
    if movie_data.get('runtime') and movie_data['runtime'] != 'N/A':
        details.append(f"⏱️ **Runtime:** {movie_data['runtime']}")
    
    details.append(f"🔍 **Source:** {source}")
    
    return '\n'.join(details)
