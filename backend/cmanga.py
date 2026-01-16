"""
CManga Source - Implementation of BaseSource for cmanga.com
"""

import httpx
import json
from typing import List, Dict, Optional
from base_source import BaseSource


class CMangaSource(BaseSource):
    """Manga source implementation for CManga API"""
    
    name = "CManga"
    language = "VI"
    base_url = "https://cmanga.com"
    api_url = "https://cmanga.com/api"
    icon = "https://cmanga.com/favicon.ico"
    
    cache_file = "cmanga_cache.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://cmanga.com/"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 18) -> List[Dict]:
        """Fetch popular manga from CManga"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                # CManga home/trending
                offset = (page - 1) * limit
                params = {
                    "type": "all",
                    "limit": limit,
                    "offset": offset,
                    "sort": "new"
                }
                
                # Note: CManga API might be slightly different now. 
                # Let's try the modern endpoint if this fails.
                resp = await client.get(f"{self.api_url}/home_manga", params=params)
                if resp.status_code != 200:
                    return {"active_manga": [], "new_manga": []}
                    
                data = resp.json()
                
                results = []
                for item in data:
                    # Item structure: { url, name, image, last_chapter, ... }
                    slug = item.get('url') # Slug in CManga is 'url'
                    if not slug: continue
                    
                    cover_url = f"https://cmanga.com/assets/tmp/comic/{item.get('image')}.jpg"
                    if not item.get('image'):
                        cover_url = "https://via.placeholder.com/200x300"
                    
                    results.append({
                        "id": slug,
                        "title": item.get('name', 'Unknown'),
                        "cover": cover_url,
                        "latest_chapter": f"Ch. {item.get('last_split', '?')}",
                        "updated_at": item.get('time', '')
                    })
                
                response = {
                    "active_manga": results,
                    "new_manga": []
                }
                
                self.set_cache(cache_key, response)
                return response
                
            except Exception as e:
                print(f"[CManga] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info from CManga (manga_id is slug)"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                # manga_id here is the slug URL
                resp = await client.get(f"{self.api_url}/manga_detail", params={"url": manga_id})
                data = resp.json()
                
                if not data or 'id' not in data: return None
                
                id_num = data['id']
                title = data.get('name', 'Unknown')
                desc = data.get('description', 'Chưa có mô tả.').replace('<p>','').replace('</p>','')
                cover_url = f"https://cmanga.com/assets/tmp/comic/{data.get('image')}.jpg"
                
                # Fetch Chapters
                chap_resp = await client.get(f"{self.api_url}/chapter_list", params={"manga_id": id_num})
                chap_data = chap_resp.json()
                
                chapters = []
                for chap in chap_data:
                    # chap: { id, chapter_num, chapter_name, time, ... }
                    chapters.append({
                        "id": str(chap['id']),
                        "title": f"Ch. {chap.get('chapter_num', '?')} - {chap.get('chapter_name', '') or ''}",
                        "date": chap.get('time', '')[:10]
                    })
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover_url,
                    "rating": 5.0,
                    "author": data.get('author', 'Unknown'),
                    "description": desc,
                    "chapters": chapters
                }
            except Exception as e:
                print(f"[CManga] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from CManga"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                resp = await client.get(f"{self.api_url}/chapter_detail", params={"chapter_id": chapter_id})
                data = resp.json()
                
                # data is often a list of image names or an object with images
                # New CManga structure: images are encrypted or in a specific format
                # Let's try to find them
                
                pages = []
                # Simple case: list of strings
                if isinstance(data, list):
                    for img in data:
                        pages.append(f"https://cmanga.com/assets/tmp/chapter/{chapter_id}/{img}")
                elif isinstance(data, dict) and 'content' in data:
                    # Content might be a comma-separated list
                    images = data['content'].split(',')
                    for img in images:
                         pages.append(f"https://cmanga.com/assets/tmp/chapter/{chapter_id}/{img}")
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
            except Exception as e:
                print(f"[CManga] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}


# Singleton instance
cmanga = CMangaSource()
