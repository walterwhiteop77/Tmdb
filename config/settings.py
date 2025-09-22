import os
from dataclasses import dataclass
from typing import List

@dataclass
class Settings:
    """Application settings."""
    BOT_TOKEN: str
    TMDB_API_KEY: str
    MONGODB_URL: str
    ADMIN_USER_ID: int
    WEBHOOK_URL: str = None
    PORT: int = 8000
    
    # Default templates
    DEFAULT_CAPTION: str = """🎬 **{title}** ({year})
🌐 **Language:** {language}
⭐ **Rating:** {rating}/10
🎭 **Genre:** {genre}
👨‍🎬 **Director:** {director}
📝 **Plot:** {plot}"""
    
    DEFAULT_LANDSCAPE_CAPTION: str = "🎬 {title} | {year} | ⭐{rating}"
    
    # TMDB settings
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_IMAGE_BASE_URL: str = "https://image.tmdb.org/t/p/original"
    
    # IMDb settings
    IMDB_BASE_URL: str = "https://www.imdb.com"
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Load settings from environment variables."""
        return cls(
            BOT_TOKEN=os.getenv("BOT_TOKEN"),
            TMDB_API_KEY=os.getenv("TMDB_API_KEY"),
            MONGODB_URL=os.getenv("MONGODB_URL"),
            ADMIN_USER_ID=int(os.getenv("ADMIN_USER_ID", "0")),
            WEBHOOK_URL=os.getenv("WEBHOOK_URL"),
            PORT=int(os.getenv("PORT", "8000"))
        )

# Global settings instance
SETTINGS = Settings.from_env()

# Validate required settings
if not all([SETTINGS.BOT_TOKEN, SETTINGS.TMDB_API_KEY, SETTINGS.MONGODB_URL]):
    raise ValueError("Missing required environment variables")

if not SETTINGS.ADMIN_USER_ID:
    raise ValueError("ADMIN_USER_ID must be set")
