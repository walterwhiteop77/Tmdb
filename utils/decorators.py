import functools
import logging
from telegram import Update
from telegram.ext import ContextTypes

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

def admin_only(func):
    """Decorator to restrict commands to admin users only."""
    
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if not user:
            logger.warning("Received update without user information")
            return
        
        if user.id != SETTINGS.ADMIN_USER_ID:
            await update.message.reply_text(
                "❌ This command is restricted to admin use only."
            )
            logger.warning(f"Unauthorized access attempt by user {user.id} (@{user.username})")
            return
        
        return await func(update, context)
    
    return wrapper

def log_command(func):
    """Decorator to log command usage."""
    
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        command = update.message.text.split()[0] if update.message and update.message.text else "unknown"
        
        logger.info(f"User {user.id} (@{user.username}) executed command: {command}")
        
        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Error executing command {command} for user {user.id}: {e}")
            await update.message.reply_text(
                f"❌ An error occurred while executing the command: {str(e)}"
            )
            raise
    
    return wrapper

def rate_limit(calls_per_minute: int = 10):
    """Decorator to implement rate limiting."""
    from collections import defaultdict
    import time
    
    call_times = defaultdict(list)
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id = update.effective_user.id
            current_time = time.time()
            
            # Clean old entries
            call_times[user_id] = [
                t for t in call_times[user_id] 
                if current_time - t < 60  # Last minute
            ]
            
            # Check rate limit
            if len(call_times[user_id]) >= calls_per_minute:
                await update.message.reply_text(
                    f"⏰ Rate limit exceeded. Please wait before making another request."
                )
                logger.warning(f"Rate limit exceeded for user {user_id}")
                return
            
            # Add current call time
            call_times[user_id].append(current_time)
            
            return await func(update, context)
        
        return wrapper
    return decorator

def typing_action(func):
    """Decorator to automatically send typing action during command execution."""
    
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from telegram.constants import ChatAction
        
        # Send typing action
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action=ChatAction.TYPING
        )
        
        return await func(update, context)
    
    return wrapper

def error_handler(func):
    """Decorator to handle and log errors gracefully."""
    
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            return await func(update, context)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            
            # Send user-friendly error message
            error_message = "❌ Something went wrong. Please try again later."
            
            if "timeout" in str(e).lower():
                error_message = "⏰ Request timed out. Please try again."
            elif "not found" in str(e).lower():
                error_message = "🔍 Item not found. Please check your search terms."
            elif "network" in str(e).lower() or "connection" in str(e).lower():
                error_message = "🌐 Network error. Please try again later."
            
            try:
                await update.message.reply_text(error_message)
            except Exception as reply_error:
                logger.error(f"Failed to send error message: {reply_error}")
    
    return wrapper

def validate_args(min_args: int = 0, max_args: int = None, usage_text: str = None):
    """Decorator to validate command arguments."""
    
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            args = context.args or []
            
            if len(args) < min_args:
                message = usage_text or f"❌ This command requires at least {min_args} argument(s)."
                await update.message.reply_text(message)
                return
            
            if max_args is not None and len(args) > max_args:
                message = usage_text or f"❌ This command accepts at most {max_args} argument(s)."
                await update.message.reply_text(message)
                return
            
            return await func(update, context)
        
        return wrapper
    return decorator
