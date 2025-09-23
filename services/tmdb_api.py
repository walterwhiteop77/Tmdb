import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional

from config.settings import SETTINGS
from config.database import cache_movie_data, get_cached_movie_data

logger = logging.getLogger(__name__)

class TMDBService:
    """Service for interacting with TMDB API."""
    
    def __init__(self):
        self.api_key = SETTINGS.TMDB_API_KEY
        self.base_url = SETTINGS.TMDB_BASE_URL
        self.image_base_url = SETTINGS.TMDB_IMAGE_BASE_URL
        self.session = None
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, endpoint: str, params: dict = None) -> dict:
        """Make API request to TMDB."""
        session = await self._get_session()
        
        default_params = {"api_key": self.api_key}
        if params:
            default_params.update(params)
        
        url = f"{self.base_url}/{endpoint}"
        
        try:
            logger.info(f"Making TMDB request to: {endpoint} with params: {params}")
            async with session.get(url, params=default_params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"TMDB response: {data.get('total_results', 0)} results")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"TMDB API error: {response.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Error making TMDB request: {e}")
            return None
    
    async def search_movie(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for a movie by title."""
        cache_key = f"tmdb_movie_search_{title}_{year or 'no_year'}"
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get('data')
        
        params = {"query": title}
        if year:
            params["year"] = year
        
        result = await self._make_request("search/movie", params)
        
        if result and result.get("results"):
            movie_data = result["results"][0]  # Get first result
            details = await self.get_movie_details(movie_data["id"])
            
            if details:
                await cache_movie_data(cache_key, {"data": details})
                return details
        
        return None
    
    async def search_tv(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for a TV show by title."""
        cache_key = f"tmdb_tv_search_{title}_{year or 'no_year'}"
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get('data')
        
        params = {"query": title}
        if year:
            params["first_air_date_year"] = year
        
        result = await self._make_request("search/tv", params)
        
        if result and result.get("results"):
            tv_data = result["results"][0]  # Get first result
            details = await self.get_tv_details(tv_data["id"])
            
            if details:
                await cache_movie_data(cache_key, {"data": details})
                return details
        
        return None
    
    async def get_movie_details(self, movie_id: int) -> Optional[Dict]:
        """Get detailed movie information."""
        cache_key = f"tmdb_movie_{movie_id}"
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get('data')
        
        # Get basic details and credits in parallel
        movie_task = self._make_request(f"movie/{movie_id}")
        credits_task = self._make_request(f"movie/{movie_id}/credits")
        
        movie_details, credits = await asyncio.gather(movie_task, credits_task)
        
        if not movie_details:
            return None
        
        # Format the data
        formatted_data = {
            "type": "movie",
            "title": movie_details.get("title", "N/A"),
            "original_title": movie_details.get("original_title", "N/A"),
            "year": movie_details.get("release_date", "")[:4] if movie_details.get("release_date") else "N/A",
            "language": movie_details.get("original_language", "N/A").upper(),
            "genres": ", ".join([g["name"] for g in movie_details.get("genres", [])]),
            "rating": movie_details.get("vote_average", "N/A"),
            "plot": movie_details.get("overview", "N/A"),
            "runtime": f"{movie_details.get('runtime', 0)} min" if movie_details.get('runtime') else "N/A",
            "poster_url": f"{self.image_base_url}{movie_details.get('poster_path')}" if movie_details.get('poster_path') else None,
            "backdrop_url": f"{self.image_base_url}{movie_details.get('backdrop_path')}" if movie_details.get('backdrop_path') else None,
            "tmdb_id": movie_id,
        }
        
        # Add director and cast from credits
        if credits:
            crew = credits.get("crew", [])
            directors = [person["name"] for person in crew if person["job"] == "Director"]
            formatted_data["director"] = ", ".join(directors) if directors else "N/A"
            
            cast = credits.get("cast", [])[:5]  # Top 5 cast members
            formatted_data["cast"] = ", ".join([person["name"] for person in cast]) if cast else "N/A"
        else:
            formatted_data["director"] = "N/A"
            formatted_data["cast"] = "N/A"
        
        await cache_movie_data(cache_key, {"data": formatted_data})
        return formatted_data
    
    async def get_tv_details(self, tv_id: int, season: Optional[int] = None, episode: Optional[int] = None) -> Optional[Dict]:
        """Get detailed TV show information."""
        cache_key = f"tmdb_tv_{tv_id}_{season or 0}_{episode or 0}"
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get('data')
        
        # Get TV show details
        tv_details = await self._make_request(f"tv/{tv_id}")
        if not tv_details:
            return None
        
        formatted_data = {
            "type": "tv",
            "title": tv_details.get("name", "N/A"),
            "original_title": tv_details.get("original_name", "N/A"),
            "year": tv_details.get("first_air_date", "")[:4] if tv_details.get("first_air_date") else "N/A",
            "language": tv_details.get("original_language", "N/A").upper(),
            "genres": ", ".join([g["name"] for g in tv_details.get("genres", [])]),
            "rating": tv_details.get("vote_average", "N/A"),
            "plot": tv_details.get("overview", "N/A"),
            "poster_url": f"{self.image_base_url}{tv_details.get('poster_path')}" if tv_details.get('poster_path') else None,
            "backdrop_url": f"{self.image_base_url}{tv_details.get('backdrop_path')}" if tv_details.get('backdrop_path') else None,
            "tmdb_id": tv_id,
            "seasons": tv_details.get("number_of_seasons", "N/A"),
            "episodes": tv_details.get("number_of_episodes", "N/A"),
        }
        
        # Add creators
        creators = tv_details.get("created_by", [])
        formatted_data["director"] = ", ".join([creator["name"] for creator in creators]) if creators else "N/A"
        
        # If specific season/episode requested, get additional details
        if season and episode:
            episode_details = await self._make_request(f"tv/{tv_id}/season/{season}/episode/{episode}")
            if episode_details:
                formatted_data["episode_title"] = episode_details.get("name", "N/A")
                formatted_data["episode_plot"] = episode_details.get("overview", formatted_data["plot"])
                formatted_data["season"] = season
                formatted_data["episode"] = episode
        
        await cache_movie_data(cache_key, {"data": formatted_data})
        return formatted_data
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()

# Global TMDB service instance
tmdb_service = TMDBService()
