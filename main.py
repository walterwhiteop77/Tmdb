import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import signal
import sys

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

class BotRunner:
    def __init__(self):
        self.application = None
        self.web_runner = None
        self.running = False

    async def health_check(self, request):
        """Health check endpoint for Render."""
        return web.Response(text="Bot is running!", status=200)

    async def start_web_server(self):
        """Start a simple web server for health checks."""
        app = web.Application()
        app.router.add_get('/health', self.health_check)
        app.router.add_get('/', self.health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        port = int(os.environ.get("PORT", 8000))
        site = web.TCPSite(runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"Web server started on port {port}")
        
        return runner

    async def setup_bot(self):
        """Set up the bot application."""
        # Create application
        self.application = Application.builder().token(SETTINGS.BOT_TOKEN).build()
        
        # Command handlers
        self.application.add_handler(CommandHandler("start", start))
        self.application.add_handler(CommandHandler("help", help_command))
        self.application.add_handler(CommandHandler("status", admin_only(status)))
        
        # Admin command handlers
        self.application.add_handler(CommandHandler("setcaption", admin_only(set_caption)))
        self.application.add_handler(CommandHandler("landscape", admin_only(set_landscape)))
        self.application.add_handler(CommandHandler("setlandcaption", admin_only(set_landscape_caption)))
        self.application.add_handler(CommandHandler("template", admin_only(view_templates)))
        
        # Message handler for movie/TV show requests
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_movie_request))
        
        # Error handler
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            logger.error(f"Update {update} caused error {context.error}")
        
        self.application.add_error_handler(error_handler)

    async def start(self):
        """Start the bot and web server."""
        try:
            # Initialize database
            await init_database()
            
            # Start web server for health checks
            self.web_runner = await self.start_web_server()
            
            # Setup bot
            await self.setup_bot()
            
            # Start the bot
            logger.info("Starting bot...")
            self.running = True
            
            # Initialize the application
            await self.application.initialize()
            await self.application.start()
            
            # Start the updater
            await self.application.updater.start_polling(drop_pending_updates=True)
            
            # Keep running until stopped
            while self.running:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            await self.cleanup()
            raise

    async def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")
        self.running = False
        
        if self.application:
            try:
                if self.application.updater.running:
                    await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.error(f"Error stopping application: {e}")
        
        if self.web_runner:
            try:
                await self.web_runner.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up web runner: {e}")

    def signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False

async def main():
    """Main function."""
    bot_runner = BotRunner()
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, bot_runner.signal_handler)
    signal.signal(signal.SIGINT, bot_runner.signal_handler)
    
    try:
        await bot_runner.start()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
    finally:
        await bot_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
