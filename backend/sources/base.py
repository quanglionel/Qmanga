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
import asyncio
from typing import List, Dict, Optional, Any

# Optional imports for Cloudflare bypass
try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

try:
    import cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

try:
    import httpx
except ImportError:
    httpx = None

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
        # Ensure cache path is in data/ folder relative to backend root
        # We assume this code runs from backend root or nearby
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.join(base_dir, "data")
        if not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            
        self.full_cache_path = os.path.join(data_dir, self.cache_file)
        
        if os.path.exists(self.full_cache_path):
            try:
                with open(self.full_cache_path, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
            except:
                self._cache = {}
    
    def save_cache(self):
        """Save cache to file"""
        try:
            # Re-ensure path exists
            if not hasattr(self, 'full_cache_path'):
                base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                data_dir = os.path.join(base_dir, "data")
                self.full_cache_path = os.path.join(data_dir, self.cache_file)

            with open(self.full_cache_path, 'w', encoding='utf-8') as f:
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
    
    # ==================== FETCH UTILITIES ====================

    async def _fetch_html(self, url: str, method: str = "GET", data: Any = None, custom_headers: dict = None, cookies: dict = None) -> Optional[str]:
        """
        Fetch HTML with triple fallback: curl_cffi -> cloudscraper -> httpx.
        Optimized for Cloudflare bypass on cloud platforms.
        """
        import random
        await asyncio.sleep(random.uniform(0.2, 0.6))

        # 1. Try curl_cffi (Ultimate Bypass)
        if HAS_CURL_CFFI:
            # We try a few different fingerprints if one fails
            fingerprints = ["chrome120", "chrome116", "safari_ios_16_0", "edge101"]
            for target in fingerprints:
                try:
                    async with AsyncSession(impersonate=target, verify=False) as client:
                        # CRITICAL: We only pass Referer and essential headers, 
                        # let curl_cffi handle UA/Accept/Sec-Fetch to match fingerprint.
                        headers = {}
                        if custom_headers:
                            # Filter out headers that might conflict with impersonation
                            for k, v in custom_headers.items():
                                if k.lower() not in ["user-agent", "accept-encoding"]:
                                    headers[k] = v
                        
                        if method.upper() == "POST":
                            resp = await client.post(url, headers=headers, data=data, cookies=cookies, timeout=30)
                        else:
                            resp = await client.get(url, headers=headers, cookies=cookies, timeout=30)
                            
                        if resp.status_code == 200:
                            if "Cloudflare" in resp.text and "Checking your browser" in resp.text:
                                continue # Try next fingerprint
                            return resp.text
                        
                        if resp.status_code == 403:
                             print(f"[{self.name}] curl_cffi ({target}): 403 Forbidden")
                except Exception as e:
                    print(f"[{self.name}] curl_cffi ({target}) error: {str(e)[:50]}")
                    continue

        # 2. Try cloudscraper (Fallback)
        if HAS_CLOUDSCRAPER:
            try:
                def sync_fetch():
                    scraper = cloudscraper.create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'mobile': True})
                    s_headers = {}
                    if custom_headers and "Referer" in custom_headers: 
                        s_headers["Referer"] = custom_headers["Referer"]
                    
                    if method.upper() == "POST":
                        return scraper.post(url, headers=s_headers, data=data, cookies=cookies, timeout=20)
                    else:
                        return scraper.get(url, headers=s_headers, cookies=cookies, timeout=20)
                
                loop = asyncio.get_event_loop()
                resp = await loop.run_in_executor(None, sync_fetch)
                if resp.status_code == 200:
                    return resp.text
            except Exception as e:
                print(f"[{self.name}] cloudscraper error: {str(e)[:50]}")

        # 3. Last resort: httpx
        if httpx:
            try:
                async with httpx.AsyncClient(timeout=25.0, follow_redirects=True, verify=False) as client:
                    h = custom_headers if custom_headers else {}
                    if method.upper() == "POST":
                        resp = await client.post(url, data=data, headers=h)
                    else:
                        resp = await client.get(url, headers=h)
                    if resp.status_code == 200:
                        return resp.text
            except: pass
        
        return None
    
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
