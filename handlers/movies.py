import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
import aiohttp

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

async def simple_movie_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple movie test without complex dependencies."""
    user = update.effective_user
    
    # Check if user is admin
    if user.id != SETTINGS.ADMIN_USER_ID:
        await update.message.reply_text("❌ This bot is restricted to admin use only.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /test <movie title>")
        return
    
    title = " ".join(context.args)
    
    # Send typing action
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    msg = await update.message.reply_text(f"🔍 Testing search for: {title}")
    
    try:
        # Test TMDB API directly
        tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={SETTINGS.TMDB_API_KEY}&query={title}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(tmdb_url) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    
                    if results:
                        movie = results[0]
                        result_text = f"""✅ TMDB API Working!

🎬 Found: {movie.get('title', 'Unknown')}
📅 Year: {movie.get('release_date', 'Unknown')[:4] if movie.get('release_date') else 'Unknown'}
⭐ Rating: {movie.get('vote_average', 'N/A')}
📝 Plot: {movie.get('overview', 'No plot available')[:200]}...

✅ Search functionality is working!
The issue is likely in the complex handler logic."""
                        
                        await msg.edit_text(result_text)
                    else:
                        await msg.edit_text(f"❌ No results found for '{title}' on TMDB")
                        
                elif response.status == 401:
                    await msg.edit_text("❌ TMDB API Key is invalid!")
                else:
                    error_text = await response.text()
                    await msg.edit_text(f"❌ TMDB API Error {response.status}: {error_text[:200]}")
                    
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)}")
        logger.error(f"Simple test error: {e}")
