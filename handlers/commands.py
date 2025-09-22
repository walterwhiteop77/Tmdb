import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    
    # Check if user is admin
    if user.id != SETTINGS.ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ This bot is restricted to admin use only."
        )
        return
    
    welcome_message = """
🎬 **Welcome to IMDb-TMDB Poster Bot!**

I can help you fetch movie and TV show details from IMDb and TMDB, then generate beautiful posters with custom captions.

**Available Commands:**
• `/setcaption <template>` - Set custom caption template
• `/landscape on/off` - Toggle landscape mode  
• `/setlandcaption <template>` - Set landscape caption
• `/template` - View current templates
• `/status` - Check bot status
• `/help` - Show this help message

**Template Variables:**
• `{title}` - Movie/TV show title
• `{year}` - Release year
• `{language}` - Language
• `{genre}` - Genres
• `{rating}` - Rating
• `{director}` - Director
• `{cast}` - Cast members
• `{plot}` - Plot summary
• `{season}` - Season (TV shows)
• `{episode}` - Episode (TV shows)

**Usage:**
Just send me the name of any movie or TV show!

Examples:
• `Avengers Endgame`
• `Breaking Bad S01E01`
• `The Dark Knight 2008`
    """
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user = update.effective_user
    
    if user.id != SETTINGS.ADMIN_USER_ID:
        await update.message.reply_text(
            "❌ This bot is restricted to admin use only."
        )
        return
    
    help_text = """
🎬 **IMDb-TMDB Poster Bot Help**

**Commands:**
• `/start` - Show welcome message
• `/help` - Show this help
• `/setcaption <template>` - Set caption template
• `/landscape on/off` - Toggle landscape mode
• `/setlandcaption <template>` - Set landscape caption  
• `/template` - View current templates
• `/status` - Check bot status

**Template Variables:**
```
{title} - Title of the movie/show
{year} - Release year
{language} - Original language
{genre} - Genres (comma separated)
{rating} - IMDb/TMDB rating
{director} - Director name(s)
{cast} - Main cast members
{plot} - Plot summary
{runtime} - Duration (movies)
{season} - Season number (TV)
{episode} - Episode number (TV)
{seasons} - Total seasons (TV)
{episodes} - Total episodes (TV)
```

**Example Templates:**
```
🎬 {title} ({year})
⭐ {rating}/10 | 🌐 {language}
🎭 {genre}
👨‍🎬 {director}
📝 {plot}
```

**Landscape Mode:**
When enabled, the bot will:
• Use backdrop images when available
• Create landscape-oriented posters
• Overlay caption on the image
• Perfect for widescreen displays

**Usage Examples:**
• `Iron Man` - Search for Iron Man movie
• `Game of Thrones S01E01` - Specific episode
• `The Matrix 1999` - Movie with year
• `Friends` - TV series

Just type the movie or show name and I'll fetch details and generate a poster!
    """
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - shows bot status."""
    try:
        from config.database import db
        from services.tmdb_api import tmdb_service
        from services.imdb_scraper import imdb_scraper
        
        # Check database connection
        try:
            await db.client.admin.command('ping')
            db_status = "✅ Connected"
        except:
            db_status = "❌ Disconnected"
        
        # Check if services are initialized
        tmdb_status = "✅ Ready" if tmdb_service else "❌ Not Ready"
        imdb_status = "✅ Ready" if imdb_scraper else "❌ Not Ready"
        
        # Get some stats
        try:
            config_count = await db.get_collection("configs").count_documents({})
            cache_count = await db.get_collection("movie_cache").count_documents({})
        except:
            config_count = "Error"
            cache_count = "Error"
        
        status_message = f"""
🤖 **Bot Status Report**

**Services:**
• Database: {db_status}
• TMDB API: {tmdb_status}
• IMDb Scraper: {imdb_status}

**Statistics:**
• Configurations: {config_count}
• Cached Items: {cache_count}

**Settings:**
• Admin ID: {SETTINGS.ADMIN_USER_ID}
• TMDB API: {'✅ Configured' if SETTINGS.TMDB_API_KEY else '❌ Missing'}

*All systems operational!* 🚀
        """
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text(
            f"❌ Error checking status: {str(e)}"
        )
