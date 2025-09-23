import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.database import get_user_config, update_user_config
from config.settings import SETTINGS

logger = logging.getLogger(__name__)

async def set_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setcaption command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a caption template.\n\n"
            "Usage: `/setcaption Your template with {variables}`\n\n"
            "Available variables:\n"
            "• `{title}`, `{year}`, `{language}`, `{genre}`\n"
            "• `{rating}`, `{director}`, `{cast}`, `{plot}`\n"
            "• `{season}`, `{episode}` (for TV shows)\n\n"
            "Example:\n"
            "`/setcaption 🎬 {title} ({year})\\n⭐ {rating}/10\\n🎭 {genre}`",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Join all arguments to form the template
        caption_template = ' '.join(context.args)
        
        # Replace \\n with actual newlines
        caption_template = caption_template.replace('\\n', '\n')
        
        # Update user config
        await update_user_config(
            update.effective_user.id, 
            {"caption_template": caption_template}
        )
        
        await update.message.reply_text(
            f"✅ **Caption template updated successfully!**\n\n"
            f"**New template:**\n```\n{caption_template}\n```\n\n"
            f"The template will be used for all future poster generations.",
            parse_mode='Markdown'
        )
        
        logger.info(f"User {update.effective_user.id} updated caption template")
        
    except Exception as e:
        logger.error(f"Error setting caption: {e}")
        await update.message.reply_text(
            f"❌ Error updating caption template: {str(e)}"
        )

async def set_landscape(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /landscape command."""
    if not context.args or context.args[0].lower() not in ['on', 'off']:
        await update.message.reply_text(
            "❌ Please specify 'on' or 'off'.\n\n"
            "Usage:\n"
            "• `/landscape on` - Enable landscape mode\n"
            "• `/landscape off` - Disable landscape mode\n\n"
            "**Landscape Mode Features:**\n"
            "• Uses backdrop images when available\n"
            "• Creates widescreen posters\n"
            "• Overlays caption on the image\n"
            "• Perfect for landscape displays",
            parse_mode='Markdown'
        )
        return
    
    try:
        landscape_mode = context.args[0].lower() == 'on'
        
        # Update user config
        await update_user_config(
            update.effective_user.id, 
            {"landscape_mode": landscape_mode}
        )
        
        mode_text = "enabled" if landscape_mode else "disabled"
        icon = "🖼️" if landscape_mode else "📱"
        
        await update.message.reply_text(
            f"✅ **Landscape mode {mode_text}!** {icon}\n\n"
            f"{'Posters will now use backdrop images and landscape orientation.' if landscape_mode else 'Posters will use standard portrait orientation.'}\n\n"
            f"Use `/setlandcaption` to customize the landscape caption overlay.",
            parse_mode='Markdown'
        )
        
        logger.info(f"User {update.effective_user.id} {'enabled' if landscape_mode else 'disabled'} landscape mode")
        
    except Exception as e:
        logger.error(f"Error setting landscape mode: {e}")
        await update.message.reply_text(
            f"❌ Error updating landscape mode: {str(e)}"
        )

async def set_landscape_caption(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setlandcaption command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a landscape caption template.\n\n"
            "Usage: `/setlandcaption Your compact template`\n\n"
            "**Note:** Landscape captions should be shorter as they overlay on the image.\n\n"
            "Good examples:\n"
            "• `🎬 {title} | {year} | ⭐{rating}`\n"
            "• `{title} ({year}) - {rating}/10`\n"
            "• `📽️ {title} | {genre} | {language}`",
            parse_mode='Markdown'
        )
        return
    
    try:
        # Join all arguments to form the template
        landscape_caption = ' '.join(context.args)
        
        # Replace \\n with actual newlines (though not recommended for landscape)
        landscape_caption = landscape_caption.replace('\\n', '\n')
        
        # Update user config
        await update_user_config(
            update.effective_user.id, 
            {"landscape_caption": landscape_caption}
        )
        
        await update.message.reply_text(
            f"✅ **Landscape caption updated successfully!** 🖼️\n\n"
            f"**New landscape caption:**\n```\n{landscape_caption}\n```\n\n"
            f"This will be used when landscape mode is enabled.",
            parse_mode='Markdown'
        )
        
        logger.info(f"User {update.effective_user.id} updated landscape caption")
        
    except Exception as e:
        logger.error(f"Error setting landscape caption: {e}")
        await update.message.reply_text(
            f"❌ Error updating landscape caption: {str(e)}"
        )

async def view_templates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /template command - show current templates."""
    try:
        config = await get_user_config(update.effective_user.id)
        
        landscape_status = "🖼️ Enabled" if config.get('landscape_mode', False) else "📱 Disabled"
        
        template_message = f"""
🎨 **Current Templates**

**Portrait Caption:**
```
{config.get('caption_template', SETTINGS.DEFAULT_CAPTION)}
```

**Landscape Caption:**
```
{config.get('landscape_caption', SETTINGS.DEFAULT_LANDSCAPE_CAPTION)}
```

**Landscape Mode:** {landscape_status}

**Available Variables:**
• `{{title}}` - Movie/TV title
• `{{year}}` - Release year  
• `{{language}}` - Language
• `{{genre}}` - Genres
• `{{rating}}` - Rating
• `{{director}}` - Director
• `{{cast}}` - Cast members
• `{{plot}}` - Plot summary
• `{{runtime}}` - Duration (movies)
• `{{season}}` - Season # (TV)
• `{{episode}}` - Episode # (TV)

**Modify Templates:**
• `/setcaption <template>` - Update portrait caption
• `/setlandcaption <template>` - Update landscape caption
• `/landscape on/off` - Toggle landscape mode
        """
        
        await update.message.reply_text(template_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error viewing templates: {e}")
        await update.message.reply_text(
            f"❌ Error retrieving templates: {str(e)}"
        )

async def debug_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /debug command - test search functionality."""
    if not context.args:
        await update.message.reply_text("Usage: /debug <movie title>")
        return
    
    title = " ".join(context.args)
    
    try:
        from services.tmdb_api import tmdb_service
        from services.imdb_scraper import imdb_scraper
        from config.settings import SETTINGS
        
        debug_msg = await update.message.reply_text(f"🔍 **Debug Search for: {title}**\n\n🔄 Starting tests...")
        
        # Check TMDB API Key
        api_key_status = "✅ Set" if SETTINGS.TMDB_API_KEY else "❌ Missing"
        await debug_msg.edit_text(
            f"🔍 **Debug Search for: {title}**\n\n🔑 TMDB API Key: {api_key_status}\n🔄 Testing TMDB..."
        )
        
        # Test TMDB
        tmdb_status = "❌ Failed"
        tmdb_error = ""
        try:
            # Test basic TMDB connection first
            session = await tmdb_service._get_session()
            test_url = f"{SETTINGS.TMDB_BASE_URL}/movie/popular?api_key={SETTINGS.TMDB_API_KEY}"
            
            async with session.get(test_url) as response:
                if response.status == 200:
                    tmdb_status = "✅ API Connected"
                elif response.status == 401:
                    tmdb_status = "❌ Invalid API Key"
                else:
                    tmdb_status = f"❌ API Error {response.status}"
                    
            await debug_msg.edit_text(
                f"🔍 **Debug Search for: {title}**\n\n🔑 TMDB API Key: {api_key_status}\n🌐 TMDB Connection: {tmdb_status}\n🔄 Searching TMDB..."
            )
            
            # Now try the actual search
            if tmdb_status.startswith("✅"):
                tmdb_result = await tmdb_service.search_movie(title)
                if tmdb_result:
                    tmdb_status = f"✅ Found: {tmdb_result.get('title', 'Unknown')}"
                else:
                    tmdb_status = "❌ No results"
            
        except Exception as e:
            tmdb_error = str(e)[:100]
            tmdb_status = f"❌ Error: {tmdb_error}"
        
        await debug_msg.edit_text(
            f"🔍 **Debug Search for: {title}**\n\n🔑 TMDB API Key: {api_key_status}\n🌐 TMDB: {tmdb_status}\n🔄 Testing IMDb..."
        )
        
        # Test IMDb
        imdb_status = "❌ Failed"
        try:
            # Test basic IMDb connection
            test_html = await imdb_scraper._make_request("https://www.imdb.com")
            if test_html and "IMDb" in test_html:
                imdb_status = "✅ Site accessible"
                
                # Try the search
                imdb_result = await imdb_scraper.search_and_get_details(title)
                if imdb_result:
                    imdb_status = f"✅ Found: {imdb_result.get('title', 'Unknown')}"
                else:
                    imdb_status = "❌ No results"
            else:
                imdb_status = "❌ Site inaccessible"
                
        except Exception as e:
            imdb_status = f"❌ Error: {str(e)[:50]}"
        
        # Final result
        await debug_msg.edit_text(
            f"🔍 **Debug Search for: {title}**\n\n"
            f"🔑 TMDB API Key: {api_key_status}\n"
            f"🌐 TMDB: {tmdb_status}\n"
            f"🌐 IMDb: {imdb_status}\n\n"
            f"**Next Steps:**\n"
            f"• Check TMDB API key if connection failed\n"
            f"• Try simpler titles like 'Matrix' or 'Avatar'\n"
            f"• Check Render logs for detailed errors"
        )
            
    except Exception as e:
        await update.message.reply_text(f"Debug error: {str(e)}")

async def test_tmdb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test TMDB API directly."""
    try:
        from services.tmdb_api import tmdb_service
        from config.settings import SETTINGS
        
        # Test with a known movie ID
        result = await tmdb_service.get_movie_details(299536)  # Avengers: Infinity War
        
        if result:
            await update.message.reply_text(
                f"✅ TMDB API Working!\n\n"
                f"**Test Movie:** {result.get('title')}\n"
                f"**Year:** {result.get('year')}\n"
                f"**Rating:** {result.get('rating')}\n\n"
                f"Search should work now. Try a movie title!"
            )
        else:
            await update.message.reply_text(
                f"❌ TMDB API Test Failed\n\n"
                f"API Key: {'Set' if SETTINGS.TMDB_API_KEY else 'Missing'}\n"
                f"Check your TMDB_API_KEY environment variable."
            )
            
    except Exception as e:
        await update.message.reply_text(f"TMDB test error: {str(e)}")
