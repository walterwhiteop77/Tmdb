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
