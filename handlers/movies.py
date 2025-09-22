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
        
        # Get user configuration
        config = await get_user_config(user.id)
        
        # Show searching message
        search_msg = await update.message.reply_text(
            f"🔍 Searching for **{title}**{f' ({year})' if year else ''}"
            f"{f' Season {season} Episode {episode}' if season and episode else ''}...",
            parse_mode='Markdown'
        )
        
        # Try to fetch data from both sources
        movie_data = None
        source = None
        
        # First try TMDB (faster and more reliable)
        try:
            if season or episode:
                movie_data = await tmdb_service.search_tv(title, year)
                if movie_data and season and episode:
                    # Get specific episode details
                    detailed_data = await tmdb_service.get_tv_details(
                        movie_data.get('tmdb_id'), season, episode
                    )
                    if detailed_data:
                        movie_data = detailed_data
            else:
                # Try movie first, then TV
                movie_data = await tmdb_service.search_movie(title, year)
                if not movie_data:
                    movie_data = await tmdb_service.search_tv(title, year)
            
            if movie_data:
                source = "TMDB"
        except Exception as e:
            logger.error(f"TMDB search error: {e}")
        
        # If TMDB failed, try IMDb
        if not movie_data:
            try:
                await search_msg.edit_text(
                    f"🔍 TMDB search failed, trying IMDb for **{title}**...",
                    parse_mode='Markdown'
                )
                
                movie_data = await imdb_scraper.search_and_get_details(title, year)
                if movie_data:
                    source = "IMDb"
            except Exception as e:
                logger.error(f"IMDb search error: {e}")
        
        if not movie_data:
            await search_msg.edit_text(
                f"❌ Sorry, I couldn't find **{title}**{f' ({year})' if year else ''} "
                f"on either TMDB or IMDb.\n\n"
                f"Please check the spelling or try a different format.",
                parse_mode='Markdown'
            )
            return
        
        # Update search message
        await search_msg.edit_text(
            f"✅ Found **{movie_data.get('title', 'Unknown')}** on {source}!\n"
            f"🎨 Generating poster...",
            parse_mode='Markdown'
        )
        
        # Send another typing action for poster generation
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
        
        # Generate poster
        landscape_mode = config.get('landscape_mode', False)
        caption_template = config.get('caption_template', SETTINGS.DEFAULT_CAPTION)
        landscape_caption = config.get('landscape_caption', SETTINGS.DEFAULT_LANDSCAPE_CAPTION)
        
        poster_buffer = await poster_generator.generate_poster(
            movie_data, 
            caption_template,
            landscape_mode,
            landscape_caption
        )
        
        if not poster_buffer:
            await search_msg.edit_text(
                f"✅ Found **{movie_data.get('title', 'Unknown')}** on {source}!\n"
                f"❌ Failed to generate poster. Sending details as text.",
                parse_mode='Markdown'
            )
            
            # Send text details as fallback
            details_text = _format_movie_details(movie_data, source)
            await update.message.reply_text(details_text, parse_mode='Markdown')
            return
        
        # Format caption for the photo
        photo_caption = _format_movie_details(movie_data, source)
        
        # Send poster
        await update.message.reply_photo(
            photo=poster_buffer,
            caption=photo_caption,
            parse_mode='Markdown'
        )
        
        # Delete the search message
        await search_msg.delete()
        
        logger.info(f"Successfully generated poster for {title} from {source}")
        
    except Exception as e:
        logger.error(f"Error handling movie request: {e}")
        await update.message.reply_text(
            f"❌ An error occurred while processing your request:\n`{str(e)}`",
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
