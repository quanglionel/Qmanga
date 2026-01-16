"""
Base Source - Abstract class that all manga sources must implement.
This is the "root" - all sources (otruyen, mangadex, comick, etc.) 
must extend this class and implement its methods.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import time
import json
import os

class BaseSource(ABC):
    """
    Abstract base class for manga sources.
    All manga sources must implement these methods.
    """
    
    # Source identification
    name: str = "Unknown Source"
    language: str = "Unknown"
    base_url: str = ""
    icon: str = "" # Added icon attribute
    
    # Cache settings (can be overridden per source)
    CACHE_TTL = 3600  # 1 hour default
    cache_file: str = "source_cache.json"
    _cache: Dict = {}
    
    def __init__(self):
        self.load_cache()
    
    # ==================== CACHE MANAGEMENT ====================
    
    def load_cache(self):
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
            except:
                self._cache = {}
    
    def save_cache(self):
        """Save cache to file"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save cache: {e}")
    
    def get_from_cache(self, key: str) -> Optional[any]:
        """Get data from cache if not expired"""
        if key in self._cache:
            entry = self._cache[key]
            if isinstance(entry, list) and len(entry) == 2:
                timestamp, data = entry
                if time.time() - timestamp < self.CACHE_TTL:
                    return data
        return None
    
    def set_cache(self, key: str, data: any):
        """Store data in cache with timestamp"""
        self._cache[key] = [time.time(), data]
        self.save_cache()
    
    # ==================== ABSTRACT METHODS (Must be implemented) ====================
    
    @abstractmethod
    async def fetch_trending(self, page: int = 1, limit: int = 24) -> List[Dict]:
        """
        Fetch trending/latest manga list.
        
        Args:
            page: Page number (1-indexed)
            limit: Number of items per page
            
        Returns:
            List of manga dicts with keys:
            - id: str (unique identifier/slug)
            - title: str
            - cover: str (image URL)
            - latest_chapter: str (e.g., "Ch. 100" or "N/A")
            - updated_at: str (ISO timestamp or empty)
            - rating: float (optional)
        """
        pass
    
    @abstractmethod
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """
        Fetch detailed info for a specific manga.
        
        Args:
            manga_id: Unique identifier (slug or ID)
            
        Returns:
            Dict with keys:
            - id: str
            - title: str
            - cover: str
            - author: str
            - description: str
            - rating: float
            - chapters: List[Dict] with keys: id, title, date
        """
        pass
    
    @abstractmethod
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """
        Fetch pages/images for a specific chapter.
        
        Args:
            chapter_id: Chapter identifier (could be URL or ID)
            
        Returns:
            Dict with keys:
            - id: str
            - pages: List[str] (list of image URLs)
        """
        pass
    
    # ==================== OPTIONAL METHODS (Can be overridden) ====================
    
    async def search(self, query: str, page: int = 1) -> List[Dict]:
        """
        Search for manga by title. Override if source supports search.
        Default implementation returns empty list.
        """
        return []
    
    def get_source_info(self) -> Dict:
        """Get source metadata"""
        return {
            "name": self.name,
            "language": self.language,
            "base_url": self.base_url,
            "icon": getattr(self, 'icon', '')
        }
