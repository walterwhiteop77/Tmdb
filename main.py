import os
import asyncio
import logging
import aiohttp
import io
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from aiohttp import web
from PIL import Image, ImageDraw, ImageFont
import textwrap

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

# Simple in-memory storage for user settings
user_settings = {
    "caption_template": """🎬 **{title}** ({year})
⭐ **Rating:** {rating}/10
🌐 **Language:** {language}
🎭 **Genre:** {genres}
👨‍🎬 **Director:** {director}
📝 **Plot:** {plot}""",
    "landscape_mode": False,
    "landscape_caption": "🎬 {title} | {year} | ⭐{rating}"
}

async def admin_only(func):
    """Decorator to check admin access."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != ADMIN_USER_ID:
            await update.message.reply_text("❌ This bot is restricted to admin use only.")
            return
        return await func(update, context)
    return wrapper

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only bot")
        return
    
    await update.message.reply_text("""
🎬 **IMDb-TMDB Poster Bot**

**Commands:**
• `/setcaption <template>` - Set custom caption
• `/landscape on/off` - Toggle landscape mode
• `/template` - View current templates
• `/help` - Show help

**Usage:**
Just send a movie name: `Iron Man`, `Avatar`, etc.

**Variables for captions:**
`{title}`, `{year}`, `{rating}`, `{language}`, `{genres}`, `{director}`, `{plot}`
    """)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only bot")
        return
        
    await update.message.reply_text("""
🎬 **Bot Commands**

**Caption Templates:**
• `/setcaption <template>` - Set custom caption
• `/template` - View current settings

**Modes:**
• `/landscape on` - Enable landscape mode
• `/landscape off` - Disable landscape mode

**Usage Examples:**
```
/setcaption 🎬 {title} ({year})\\n⭐ {rating}/10
```

**Search:**
Just type movie names: `Iron Man`, `Matrix`, `Breaking Bad S01E01`
    """)

async def set_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setcaption command."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only bot")
        return
        
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a caption template.\n\n"
            "Usage: `/setcaption Your template with {variables}`"
        )
        return
    
    template = ' '.join(context.args).replace('\\n', '\n')
    user_settings["caption_template"] = template
    
    await update.message.reply_text(
        f"✅ **Caption template updated!**\n\n```\n{template}\n```"
    )

async def set_landscape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /landscape command."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only bot")
        return
        
    if not context.args or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text("Usage: `/landscape on` or `/landscape off`")
        return
    
    landscape_mode = context.args[0].lower() == 'on'
    user_settings["landscape_mode"] = landscape_mode
    
    status = "enabled" if landscape_mode else "disabled"
    await update.message.reply_text(f"✅ Landscape mode {status}!")

async def view_template(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /template command."""
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("❌ Admin only bot")
        return
        
    landscape_status = "🖼️ Enabled" if user_settings["landscape_mode"] else "📱 Disabled"
    
    await update.message.reply_text(f"""
🎨 **Current Settings**

**Caption Template:**
```
{user_settings["caption_template"]}
```

**Landscape Mode:** {landscape_status}

**Landscape Caption:**
```
{user_settings["landscape_caption"]}
```
    """)

async def download_image(url: str) -> Image.Image:
    """Download image from URL."""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                image_data = await response.read()
                return Image.open(io.BytesIO(image_data))
    return None

def create_clean_poster(image: Image.Image, landscape_mode: bool = False) -> io.BytesIO:
    """Create clean poster without caption burned in."""
    try:
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        if landscape_mode:
            # For landscape mode, try to get backdrop image or crop to landscape ratio
            width, height = image.size
            target_ratio = 16 / 9
            current_ratio = width / height
            
            if current_ratio < target_ratio:
                # Too tall, crop height
                new_height = int(width / target_ratio)
                top = (height - new_height) // 2
                image = image.crop((0, top, width, top + new_height))
            elif current_ratio > target_ratio:
                # Too wide, crop width  
                new_width = int(height * target_ratio)
                left = (width - new_width) // 2
                image = image.crop((left, 0, left + new_width, height))
        
        # Save clean image
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=95)
        output.seek(0)
        return output
        
    except Exception as e:
        logger.error(f"Error creating poster: {e}")
        return None

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
        # Search TMDB
        url = f"https://api.themoviedb.org/3/search/movie"
        params = {"api_key": TMDB_API_KEY, "query": title}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])
                    
                    if results:
                        movie = results[0]
                        movie_id = movie['id']
                        
                        # Get detailed info
                        detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
                        detail_params = {"api_key": TMDB_API_KEY}
                        
                        async with session.get(detail_url, params=detail_params) as detail_response:
                            if detail_response.status == 200:
                                details = await detail_response.json()
                                
                                # Format movie data
                                movie_data = {
                                    "title": details.get('title', 'Unknown'),
                                    "year": details.get('release_date', '')[:4] if details.get('release_date') else 'Unknown',
                                    "rating": details.get('vote_average', 'N/A'),
                                    "language": details.get('original_language', 'Unknown').upper(),
                                    "genres": ', '.join([g['name'] for g in details.get('genres', [])]),
                                    "director": "N/A",  # Would need credits API call
                                    "plot": details.get('overview', 'No plot available')[:300] + "..." if details.get('overview') else "No plot available"
                                }
                                
                                await msg.edit_text("✅ Found! Generating poster...")
                                await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
                                
                                # Choose image based on mode
                                if user_settings["landscape_mode"] and details.get('backdrop_path'):
                                    # Use backdrop for landscape
                                    image_url = f"https://image.tmdb.org/t/p/w1280{details.get('backdrop_path')}"
                                    image_type = "backdrop"
                                else:
                                    # Use poster for portrait
                                    image_url = f"https://image.tmdb.org/t/p/w500{details.get('poster_path')}"
                                    image_type = "poster"
                                
                                logger.info(f"Downloading {image_type} from: {image_url}")
                                image = await download_image(image_url)
                                
                                if image:
                                    # Create clean poster (no caption burned in)
                                    poster_buffer = create_clean_poster(image, user_settings["landscape_mode"])
                                    
                                    if poster_buffer:
                                        # Format caption for Telegram message
                                        if user_settings["landscape_mode"]:
                                            template = user_settings["landscape_caption"]
                                        else:
                                            template = user_settings["caption_template"]
                                        
                                        telegram_caption = template.format(**movie_data)
                                        
                                        # Send poster with caption in Telegram message
                                        await update.message.reply_photo(
                                            photo=poster_buffer,
                                            caption=telegram_caption,
                                            parse_mode='Markdown'
                                        )
                                        await msg.delete()
                                        
                                        mode_info = "🖼️ Landscape" if user_settings["landscape_mode"] else "📱 Portrait"
                                        logger.info(f"Successfully sent {mode_info} poster for: {movie_data['title']}")
                                    else:
                                        await msg.edit_text("❌ Failed to generate poster")
                                else:
                                    await msg.edit_text("❌ Failed to download poster image")
                            else:
                                await msg.edit_text("❌ Failed to get movie details")
                    else:
                        await msg.edit_text(f"❌ No results found for '{title}'")
                elif response.status == 401:
                    await msg.edit_text("❌ TMDB API Key is invalid!")
                else:
                    await msg.edit_text(f"❌ TMDB API Error {response.status}")
                    
    except Exception as e:
        await msg.edit_text(f"❌ Search error: {str(e)[:100]}")
        logger.error(f"Search error: {e}")

async def health_check(request):
    """Health check endpoint for Render."""
    return web.Response(text="Bot is running!", status=200)

async def start_web_server():
    """Start web server for Render health checks."""
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 8000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server started on port {port}")
    return runner

async def main():
    """Main function."""
    web_runner = None
    application = None
    
    try:
        # Start web server for Render
        web_runner = await start_web_server()
        
        # Create and configure application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("setcaption", set_caption))
        application.add_handler(CommandHandler("landscape", set_landscape))
        application.add_handler(CommandHandler("template", view_template))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_search))
        
        logger.info("Starting bot with all commands...")
        
        # Initialize and start polling
        async with application:
            await application.start()
            await application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running
            await asyncio.Event().wait()
        
    except Exception as e:
        logger.error(f"Bot error: {e}")
    finally:
        # Cleanup
        if application:
            try:
                await application.stop()
            except:
                pass
        if web_runner:
            try:
                await web_runner.cleanup()
            except:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
