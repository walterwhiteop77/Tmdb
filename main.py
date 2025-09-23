import os
import asyncio
import logging
import aiohttp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only bot")
        return
    
    await update.message.reply_text("""
🎬 **Movie Bot Working!**

Commands:
• Just type a movie name (e.g., "Iron Man")
• /start - This message

Status: Ready to search movies!
    """)

async def handle_movie_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle movie search requests."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only")
        return
    
    title = update.message.text.strip()
    if not title:
        return
    
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    msg = await update.message.reply_text(f"🔍 Searching for: {title}")
    
    try:
        # Direct TMDB API call
        url = f"https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": TMDB_API_KEY,
            "query": title
        }
        
        logger.info(f"Searching TMDB for: {title}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                logger.info(f"TMDB response status: {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    
                    logger.info(f"TMDB found {len(results)} results")
                    
                    if results:
                        movie = results[0]
                        
                        # Get detailed info
                        movie_id = movie['id']
                        detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                        detail_params = {"api_key": TMDB_API_KEY}
                        
                        async with session.get(detail_url, params=detail_params) as detail_response:
                            if detail_response.status == 200:
                                details = await detail_response.json()
                                
                                result_text = f"""✅ **Found: {details.get('title', 'Unknown')}**

📅 **Year:** {details.get('release_date', 'Unknown')[:4] if details.get('release_date') else 'Unknown'}
⭐ **Rating:** {details.get('vote_average', 'N/A')}/10
🌐 **Language:** {details.get('original_language', 'Unknown').upper()}
🎭 **Genres:** {', '.join([g['name'] for g in details.get('genres', [])])}
⏱️ **Runtime:** {details.get('runtime', 'Unknown')} min

📝 **Plot:** {details.get('overview', 'No plot available')[:300]}...

🔍 **Source:** TMDB
                                """
                                
                                await msg.edit_text(result_text)
                                logger.info(f"Successfully found: {details.get('title')}")
                            else:
                                await msg.edit_text(f"✅ Found movie but couldn't get details")
                    else:
                        await msg.edit_text(f"❌ No results found for '{title}' on TMDB")
                        
                elif response.status == 401:
                    await msg.edit_text("❌ TMDB API Key is invalid!")
                    logger.error("Invalid TMDB API key")
                else:
                    error_text = await response.text()
                    await msg.edit_text(f"❌ TMDB API Error {response.status}")
                    logger.error(f"TMDB API error {response.status}: {error_text}")
                    
    except Exception as e:
        await msg.edit_text(f"❌ Search error: {str(e)[:100]}")
        logger.error(f"Search error: {e}")

async def main():
    """Main function."""
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
        
        logger.info("Starting bot...")
        
        # Start polling
        await application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
