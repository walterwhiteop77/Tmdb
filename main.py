import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import threading

from config.settings import SETTINGS
from config.database import init_database
from handlers.commands import start, help_command, status
from handlers.admin import set_caption, set_landscape, set_landscape_caption, view_templates
from handlers.movies import handle_movie_request
from utils.decorators import admin_only

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint for Render."""
    return web.Response(text="Bot is running!", status=200)

async def start_web_server():
    """Start a simple web server for health checks."""
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
    """Main function to run the bot."""
    try:
        # Initialize database
        await init_database()
        
        # Start web server for health checks
        web_runner = await start_web_server()
        
        # Create application
        app = Application.builder().token(SETTINGS.BOT_TOKEN).build()
        
        # Command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", admin_only(status)))
        
        # Admin command handlers
        app.add_handler(CommandHandler("setcaption", admin_only(set_caption)))
        app.add_handler(CommandHandler("landscape", admin_only(set_landscape)))
        app.add_handler(CommandHandler("setlandcaption", admin_only(set_landscape_caption)))
        app.add_handler(CommandHandler("template", admin_only(view_templates)))
        
        # Message handler for movie/TV show requests
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_request))
        
        # Error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Update {update} caused error {context.error}")
        
        app.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Starting bot...")
        
        # Use polling for now (webhook can be configured later if needed)
        await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Cleanup
        if 'web_runner' in locals():
            await web_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import threading

from config.settings import SETTINGS
from config.database import init_database
from handlers.commands import start, help_command, status
from handlers.admin import set_caption, set_landscape, set_landscape_caption, view_templates
from handlers.movies import handle_movie_request
from utils.decorators import admin_only

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def health_check(request):
    """Health check endpoint for Render."""
    return web.Response(text="Bot is running!", status=200)

async def start_web_server():
    """Start a simple web server for health checks."""
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
    """Main function to run the bot."""
    try:
        # Initialize database
        await init_database()
        
        # Start web server for health checks
        web_runner = await start_web_server()
        
        # Create application
        app = Application.builder().token(SETTINGS.BOT_TOKEN).build()
        
        # Command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", admin_only(status)))
        
        # Admin command handlers
        app.add_handler(CommandHandler("setcaption", admin_only(set_caption)))
        app.add_handler(CommandHandler("landscape", admin_only(set_landscape)))
        app.add_handler(CommandHandler("setlandcaption", admin_only(set_landscape_caption)))
        app.add_handler(CommandHandler("template", admin_only(view_templates)))
        
        # Message handler for movie/TV show requests
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_request))
        
        # Error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Update {update} caused error {context.error}")
        
        app.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Starting bot...")
        
        # Use polling for now (webhook can be configured later if needed)
        await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Cleanup
        if 'web_runner' in locals():
            await web_runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
