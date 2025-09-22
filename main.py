import os
import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

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

async def main():
    """Main function to run the bot."""
    try:
        # Initialize database
        await init_database()
        
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
        
        # Use webhook for deployment or polling for development
        if SETTINGS.WEBHOOK_URL:
            await app.run_webhook(
                listen="0.0.0.0",
                port=int(os.environ.get("PORT", 8000)),
                webhook_url=SETTINGS.WEBHOOK_URL
            )
        else:
            await app.run_polling(allowed_updates=Update.ALL_TYPES)
            
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
