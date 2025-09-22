import aiohttp
import re
import asyncio
import logging
from bs4 import BeautifulSoup
from typing import Dict, Optional
from urllib.parse import quote

from config.settings import SETTINGS
from config.database import cache_movie_data, get_cached_movie_data

logger = logging.getLogger(__name__)

class IMDbScraper:
    """Service for scraping IMDb data without API."""
    
    def __init__(self):
        self.base_url = SETTINGS.IMDB_BASE_URL
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    async def _get_session(self):
        """Get or create aiohttp session."""
        if not self.session:
            connector = aiohttp.TCPConnector(limit=10)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session
    
    async def _make_request(self, url: str) -> Optional[str]:
        """Make HTTP request and return HTML content."""
        session = await self._get_session()
        
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"IMDb request failed: {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error making IMDb request: {e}")
            return None
    
    async def search_title(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """Search for a title and return IMDb ID."""
        cache_key = f"imdb_search_{title}_{year or 'no_year'}"
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get('imdb_id')
        
        # Clean title for search
        clean_title = re.sub(r'[^\w\s]', '', title.lower())
        search_query = quote(clean_title)
        
        search_url = f"{self.base_url}/find?q={search_query}&ref_=nv_sr_sm"
        
        html = await self._make_request(search_url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Look for title results
        results = soup.find_all('td', class_='result_text')
        
        for result in results:
            link = result.find('a')
            if not link:
                continue
            
            href = link.get('href', '')
            if not href.startswith('/title/'):
                continue
            
            # Cast
            cast_section = soup.find('section', {'data-testid': 'title-cast'})
            if cast_section:
                cast_links = cast_section.find_all('a', href=re.compile(r'/name/'))
                cast_names = []
                for link in cast_links[:5]:  # Top 5 cast members
                    name = link.get_text().strip()
                    if name and name not in cast_names:
                        cast_names.append(name)
                data["cast"] = ", ".join(cast_names) if cast_names else "N/A"
            else:
                data["cast"] = "N/A"
            
            # Language
            lang_elem = soup.find('li', {'data-testid': 'title-details-languages'})
            if lang_elem:
                lang_links = lang_elem.find_all('a')
                languages = [link.get_text().strip() for link in lang_links]
                data["language"] = ", ".join(languages) if languages else "N/A"
            else:
                data["language"] = "N/A"
            
            # Determine type (movie/tv)
            type_indicators = soup.find_all(string=re.compile(r'TV Series|TV Mini Series|TV Movie'))
            if type_indicators:
                data["type"] = "tv"
                
                # For TV shows, try to get season/episode info if available
                episodes_elem = soup.find('span', string=re.compile(r'\d+ episodes'))
                if episodes_elem:
                    episodes_match = re.search(r'(\d+) episodes', episodes_elem)
                    if episodes_match:
                        data["episodes"] = episodes_match.group(1)
            else:
                data["type"] = "movie"
            
            # Poster image
            poster_img = soup.find('img', {'data-testid': 'hero-media__poster'})
            if poster_img:
                poster_src = poster_img.get('src')
                if poster_src:
                    # Clean up IMDb image URL to get higher resolution
                    poster_src = re.sub(r'UX\d+_CR\d+,\d+,\d+,\d+_AL_', 'UX500_CR0,0,500,750_AL_', poster_src)
                    data["poster_url"] = poster_src
            
            # Cache the result
            await cache_movie_data(cache_key, {"data": data})
            return data
            
        except Exception as e:
            logger.error(f"Error parsing IMDb data for {imdb_id}: {e}")
            return None
    
    async def search_and_get_details(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Search for a title and get its details in one call."""
        imdb_id = await self.search_title(title, year)
        if not imdb_id:
            return None
        
        return await self.get_title_details(imdb_id)
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session:
            await self.session.close()

# Global IMDb scraper instance
imdb_scraper = IMDbScraper() Extract IMDb ID
            imdb_id = re.search(r'/title/(tt\d+)/', href)
            if not imdb_id:
                continue
            
            imdb_id = imdb_id.group(1)
            
            # Check if year matches (if provided)
            if year:
                year_match = re.search(r'\((\d{4})\)', result.get_text())
                if year_match and abs(int(year_match.group(1)) - year) > 1:
                    continue
            
            # Cache the result
            await cache_movie_data(cache_key, {"imdb_id": imdb_id})
            return imdb_id
        
        return None
    
    async def get_title_details(self, imdb_id: str) -> Optional[Dict]:
        """Get detailed information about a title."""
        cache_key = f"imdb_details_{imdb_id}"
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get('data')
        
        url = f"{self.base_url}/title/{imdb_id}/"
        html = await self._make_request(url)
        
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        try:
            data = {
                "imdb_id": imdb_id,
                "type": "unknown"
            }
            
            # Title
            title_elem = soup.find('h1', {'data-testid': 'hero-title-block__title'})
            if title_elem:
                data["title"] = title_elem.get_text().strip()
            else:
                # Fallback
                title_elem = soup.find('h1')
                data["title"] = title_elem.get_text().strip() if title_elem else "N/A"
            
            # Year
            year_elem = soup.find('a', href=re.compile(r'/year/'))
            if year_elem:
                year_match = re.search(r'\d{4}', year_elem.get_text())
                data["year"] = year_match.group() if year_match else "N/A"
            else:
                data["year"] = "N/A"
            
            # Rating
            rating_elem = soup.find('span', {'data-testid': 'hero-rating-bar__aggregate-rating__score'})
            if rating_elem:
                rating_text = rating_elem.get_text().strip()
                rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                data["rating"] = rating_match.group(1) if rating_match else "N/A"
            else:
                data["rating"] = "N/A"
            
            # Duration/Runtime
            duration_elem = soup.find('li', {'data-testid': 'title-techspec_runtime'})
            if duration_elem:
                duration_text = duration_elem.get_text()
                data["runtime"] = duration_text.strip()
            else:
                data["runtime"] = "N/A"
            
            # Genres
            genre_elems = soup.find_all('a', href=re.compile(r'/search/title.*genres='))
            if genre_elems:
                genres = [elem.get_text().strip() for elem in genre_elems]
                data["genres"] = ", ".join(genres)
            else:
                data["genres"] = "N/A"
            
            # Plot
            plot_elem = soup.find('span', {'data-testid': 'plot-summary'})
            if plot_elem:
                data["plot"] = plot_elem.get_text().strip()
            else:
                data["plot"] = "N/A"
            
            # Director
            director_section = soup.find('li', {'data-testid': 'title-pc-principal-credit'})
            if director_section:
                director_links = director_section.find_all('a')
                directors = [link.get_text().strip() for link in director_links if '/name/' in link.get('href', '')]
                data["director"] = ", ".join(directors) if directors else "N/A"
            else:
                data["director"] = "N/A"
            
            #
