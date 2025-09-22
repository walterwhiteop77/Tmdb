import re
from typing import Tuple, Optional

def parse_query(query: str) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[int]]:
    """
    Parse user query to extract title, year, season, and episode.
    
    Returns:
        Tuple[title, year, season, episode]
    """
    if not query or not query.strip():
        return None, None, None, None
    
    query = query.strip()
    title = None
    year = None
    season = None
    episode = None
    
    # Pattern for season/episode (S01E01 format)
    season_episode_pattern = r'[Ss](\d+)[Ee](\d+)'
    season_episode_match = re.search(season_episode_pattern, query)
    
    if season_episode_match:
        season = int(season_episode_match.group(1))
        episode = int(season_episode_match.group(2))
        # Remove season/episode from query to get clean title
        title = re.sub(season_episode_pattern, '', query).strip()
    else:
        # Pattern for "Season X Episode Y" format
        season_episode_long = r'[Ss]eason\s+(\d+)\s+[Ee]pisode\s+(\d+)'
        season_episode_long_match = re.search(season_episode_long, query, re.IGNORECASE)
        
        if season_episode_long_match:
            season = int(season_episode_long_match.group(1))
            episode = int(season_episode_long_match.group(2))
            title = re.sub(season_episode_long, '', query, flags=re.IGNORECASE).strip()
    
    # If no season/episode found, treat entire query as title initially
    if not title:
        title = query
    
    # Extract year from title (look for 4-digit year)
    year_pattern = r'\b(19|20)\d{2}\b'
    year_match = re.search(year_pattern, title)
    
    if year_match:
        year = int(year_match.group())
        # Remove year from title
        title = re.sub(year_pattern, '', title).strip()
    
    # Clean up title (remove extra spaces, punctuation at ends)
    if title:
        title = re.sub(r'\s+', ' ', title).strip()
        title = title.strip('- ')
    
    return title, year, season, episode

def extract_season_episode(text: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Extract season and episode numbers from text.
    
    Supports formats:
    - S01E01, S1E1
    - Season 1 Episode 1
    - 1x01
    """
    if not text:
        return None, None
    
    # S01E01 format
    match = re.search(r'[Ss](\d+)[Ee](\d+)', text)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # Season X Episode Y format
    match = re.search(r'[Ss]eason\s+(\d+)\s+[Ee]pisode\s+(\d+)', text, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    # 1x01 format
    match = re.search(r'(\d+)x(\d+)', text)
    if match:
        return int(match.group(1)), int(match.group(2))
    
    return None, None

def clean_filename(filename: str) -> str:
    """Clean filename by removing invalid characters."""
    if not filename:
        return "untitled"
    
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    filename = re.sub(r'\s+', '_', filename)
    
    # Limit length
    if len(filename) > 100:
        filename = filename[:100]
    
    return filename.strip('_')

def format_duration(minutes: int) -> str:
    """Format duration in minutes to hours and minutes."""
    if not minutes or minutes <= 0:
        return "N/A"
    
    hours = minutes // 60
    mins = minutes % 60
    
    if hours > 0:
        if mins > 0:
            return f"{hours}h {mins}m"
        else:
            return f"{hours}h"
    else:
        return f"{mins}m"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to specified length with ellipsis."""
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-3] + "..."

def safe_get(data: dict, key: str, default: str = "N/A") -> str:
    """Safely get value from dictionary with default."""
    value = data.get(key)
    
    if value is None or value == "" or value == "None":
        return default
    
    return str(value)

def format_list(items: list, separator: str = ", ", max_items: int = 5) -> str:
    """Format list of items as string."""
    if not items:
        return "N/A"
    
    # Take only the first max_items
    items = items[:max_items]
    
    # Filter out empty/None items
    items = [str(item).strip() for item in items if item and str(item).strip()]
    
    if not items:
        return "N/A"
    
    return separator.join(items)

def is_valid_imdb_id(imdb_id: str) -> bool:
    """Check if string is a valid IMDb ID."""
    if not imdb_id:
        return False
    
    return bool(re.match(r'^tt\d{7,}$', imdb_id))

def extract_imdb_id(text: str) -> Optional[str]:
    """Extract IMDb ID from text/URL."""
    if not text:
        return None
    
    # Look for tt followed by digits
    match = re.search(r'(tt\d{7,})', text)
    if match:
        return match.group(1)
    
    return None

def normalize_title(title: str) -> str:
    """Normalize title for better matching."""
    if not title:
        return ""
    
    # Convert to lowercase
    title = title.lower()
    
    # Remove common articles and words
    articles = ['the', 'a', 'an']
    words = title.split()
    
    if words and words[0] in articles:
        words = words[1:]
    
    # Remove special characters and extra spaces
    title = ' '.join(words)
    title = re.sub(r'[^\w\s]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    return title

def calculate_similarity(str1: str, str2: str) -> float:
    """Calculate simple similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    
    str1 = normalize_title(str1)
    str2 = normalize_title(str2)
    
    if str1 == str2:
        return 1.0
    
    # Simple word overlap calculation
    words1 = set(str1.split())
    words2 = set(str2.split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    
    return len(intersection) / len(union)

def validate_template(template: str) -> Tuple[bool, str]:
    """Validate caption template and return any errors."""
    if not template:
        return False, "Template cannot be empty"
    
    if len(template) > 1000:
        return False, "Template is too long (max 1000 characters)"
    
    # Check for valid variable syntax
    variables = re.findall(r'\{([^}]+)\}', template)
    
    valid_variables = {
        'title', 'original_title', 'year', 'language', 'genres', 'genre',
        'rating', 'plot', 'runtime', 'director', 'cast', 'season', 'episode',
        'seasons', 'episodes', 'imdb_id', 'tmdb_id', 'type'
    }
    
    invalid_vars = [var for var in variables if var not in valid_variables]
    
    if invalid_vars:
        return False, f"Invalid variables: {', '.join(invalid_vars)}"
    
    return True, "Valid template"
