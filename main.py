import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web

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
    web_runner = None
    try:
        # Initialize database
        await init_database()
        
        # Start web server for health checks
        web_runner = await start_web_server()
        
        # Create application
        application = Application.builder().token(SETTINGS.BOT_TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("status", admin_only(status)))
        
        # Admin command handlers
        application.add_handler(CommandHandler("setcaption", admin_only(set_caption)))
        application.add_handler(CommandHandler("landscape", admin_only(set_landscape)))
        application.add_handler(CommandHandler("setlandcaption", admin_only(set_landscape_caption)))
        application.add_handler(CommandHandler("template", admin_only(view_templates)))
        
        # Message handler for movie/TV show requests
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_request))
        
        # Error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Update {update} caused error {context.error}")
        
        application.add_error_handler(error_handler)
        
        # Start the bot
        logger.info("Starting bot...")
        
        # Initialize and start polling
        await application.initialize()
        await application.start()
        
        # Start polling
        await application.updater.start_polling(drop_pending_updates=True)
        
        # Keep the application running
        await application.updater.idle()
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise
    finally:
        # Cleanup
        if web_runner:
            await web_runner.cleanup()
        if 'application' in locals():
            await application.stop()
            await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
