import aiohttp
import asyncio
import logging
import re
from bs4 import BeautifulSoup
from typing import Optional, Dict
from services.cache import cache_movie_data, get_cached_movie_data

logger = logging.getLogger(__name__)


class IMDbScraper:
    BASE_URL = "https://www.imdb.com"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def init_session(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def fetch(self, url: str) -> Optional[str]:
        """Fetch page content from IMDb."""
        await self.init_session()
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"Failed to fetch {url} with status {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Request error fetching {url}: {e}")
            return None

    async def search_title(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """Search IMDb for a title and return the IMDb ID of the best match."""
        query = f"{title} {year}" if year else title
        search_url = f"{self.BASE_URL}/find?q={query}&s=tt&ttype=ft&ref_=fn_ft"
        html = await self.fetch(search_url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")
        result = soup.find("td", class_="result_text")
        if result and result.a:
            href = result.a.get("href")
            imdb_id_match = re.search(r"/title/(tt\d+)/", href)
            if imdb_id_match:
                return imdb_id_match.group(1)

        return None

    async def get_title_details(self, imdb_id: str) -> Optional[Dict]:
        """Fetch and parse IMDb title details by IMDb ID."""
        cache_key = f"imdb:{imdb_id}"

        # Check cache first
        cached = await get_cached_movie_data(cache_key)
        if cached:
            return cached.get("data")

        try:
            url = f"{self.BASE_URL}/title/{imdb_id}/"
            html = await self.fetch(url)
            if not html:
                return None

            soup = BeautifulSoup(html, "html.parser")
            data: Dict = {}

            # Title
            title_elem = soup.find("h1")
            if title_elem:
                data["title"] = title_elem.get_text(strip=True)

            # Year
            year_elem = soup.find("span", {"class": "sc-8c396aa2-2"})
            if year_elem:
                data["year"] = year_elem.get_text(strip=True)

            # Rating
            rating_elem = soup.find("span", {"class": "sc-bde20123-1"})
            if rating_elem:
                data["rating"] = rating_elem.get_text(strip=True)

            # Genre
            genres = soup.find_all("a", href=re.compile(r"genres="))
            if genres:
                data["genres"] = [g.get_text(strip=True) for g in genres]

            # Language
            lang_elem = soup.find("li", {"data-testid": "title-details-languages"})
            if lang_elem:
                data["language"] = lang_elem.get_text(strip=True)
            else:
                data["language"] = "N/A"

            # Type (movie / tv)
            type_indicators = soup.find_all(
                string=re.compile(r"TV Series|TV Mini Series|TV Movie")
            )
            if type_indicators:
                data["type"] = "tv"
                episodes_elem = soup.find("span", string=re.compile(r"\d+ episodes"))
                if episodes_elem:
                    episodes_match = re.search(r"(\d+) episodes", episodes_elem.text)
                    if episodes_match:
                        data["episodes"] = episodes_match.group(1)
            else:
                data["type"] = "movie"

            # Poster
            poster_img = soup.find("img", {"data-testid": "hero-media__poster"})
            if poster_img:
                poster_src = poster_img.get("src")
                if poster_src:
                    poster_src = re.sub(
                        r"UX\d+_CR\d+,\d+,\d+,\d+_AL_",
                        "UX500_CR0,0,500,750_AL_",
                        poster_src,
                    )
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


# Create a single instance for usage
imdb_scraper = IMDbScraper()
