import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
import logging

from config.settings import SETTINGS

logger = logging.getLogger(__name__)

class Database:
    """Database connection handler."""
    
    def __init__(self):
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(SETTINGS.MONGODB_URL, serverSelectionTimeoutMS=5000)
            # Test the connection
            await self.client.admin.command('ping')
            self.db = self.client.telegram_bot
            logger.info("Connected to MongoDB successfully")
            
            # Create indexes
            await self.create_indexes()
            
        except ServerSelectionTimeoutError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def create_indexes(self):
        """Create database indexes."""
        try:
            # Create indexes for efficient queries
            await self.db.configs.create_index("user_id", unique=True)
            await self.db.movie_cache.create_index("imdb_id", unique=True)
            await self.db.movie_cache.create_index("tmdb_id", unique=True)
            await self.db.movie_cache.create_index([("created_at", 1)], expireAfterSeconds=86400)  # 24h TTL
            
            logger.info("Database indexes created successfully")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_collection(self, name: str):
        """Get a collection by name."""
        return self.db[name]

# Global database instance
db = Database()

async def init_database():
    """Initialize database connection."""
    await db.connect()

async def close_database():
    """Close database connection."""
    await db.disconnect()

# Helper functions for common database operations
async def get_user_config(user_id: int):
    """Get user configuration."""
    config = await db.get_collection("configs").find_one({"user_id": user_id})
    if not config:
        # Create default config
        config = {
            "user_id": user_id,
            "caption_template": SETTINGS.DEFAULT_CAPTION,
            "landscape_mode": False,
            "landscape_caption": SETTINGS.DEFAULT_LANDSCAPE_CAPTION,
            "created_at": asyncio.get_event_loop().time()
        }
        await db.get_collection("configs").insert_one(config)
    return config

async def update_user_config(user_id: int, updates: dict):
    """Update user configuration."""
    return await db.get_collection("configs").update_one(
        {"user_id": user_id},
        {"$set": updates},
        upsert=True
    )

async def cache_movie_data(key: str, data: dict, ttl: int = 3600):
    """Cache movie data with TTL."""
    import time
    data["cached_at"] = time.time()
    data["ttl"] = ttl
    
    return await db.get_collection("movie_cache").update_one(
        {"key": key},
        {"$set": data},
        upsert=True
    )

async def get_cached_movie_data(key: str):
    """Get cached movie data."""
    import time
    cached = await db.get_collection("movie_cache").find_one({"key": key})
    
    if cached and (time.time() - cached.get("cached_at", 0)) < cached.get("ttl", 3600):
        return cached
    
    return None
