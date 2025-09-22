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
