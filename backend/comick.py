"""
Comick Source - Implementation of BaseSource for api.comick.io
"""

import httpx
from typing import List, Dict, Optional
from base_source import BaseSource


class ComickSource(BaseSource):
    """Manga source implementation for Comick.io API"""
    
    name = "Comick"
    language = "Multi"
    base_url = "https://api.comick.io"
    icon = "https://comick.io/static/icons/favicon-32x32.png"
    
    cache_file = "comick_cache.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": "https://comick.io/"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 18) -> List[Dict]:
        """Fetch trending manga from Comick"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        async with httpx.AsyncClient(headers=self.headers, timeout=60.0) as client:
            try:
                # Use search endpoint with trending sort - often more reliable and supports pagination
                params = {
                    "sort": "trending",
                    "type": "comic",
                    "limit": limit,
                    "page": page,
                    "tachiyomi": "true"
                }
                
                resp = await client.get(f"{self.base_url}/v1.0/search", params=params)
                if resp.status_code != 200:
                    print(f"[Comick] Failed to fetch search: {resp.status_code}")
                    return {"active_manga": [], "new_manga": []}
                    
                data = resp.json()
                # Search result is usually a direct list of items
                source_list = data if isinstance(data, list) else data.get('data', [])
                
                results = []
                for item in source_list:
                    slug = item.get('slug')
                    if not slug: continue
                    
                    # Ensure we have cover
                    cover_key = ""
                    if item.get('md_covers'):
                        cover_key = item['md_covers'][0].get('b2key')
                    
                    cover_url = f"https://meo.comick.pictures/{cover_key}" if cover_key else "https://via.placeholder.com/200x300"
                    
                    results.append({
                        "id": slug,
                        "title": item.get('title', 'Unknown'),
                        "cover": cover_url,
                        "latest_chapter": f"Ch. {item.get('last_chapter', '?')}" if item.get('last_chapter') else "N/A",
                        "updated_at": item.get('updated_at', '')
                    })
                
                response = {
                    "active_manga": results,
                    "new_manga": []
                }
                
                self.set_cache(cache_key, response)
                return response
                
            except Exception as e:
                print(f"[Comick] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info from Comick (manga_id is slug)"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/comic/{manga_id}")
                data = resp.json()
                
                comic = data.get('comic', {})
                if not comic: return None
                
                hid = comic.get('hid')
                title = comic.get('title', 'Unknown')
                desc = comic.get('desc', 'Chưa có mô tả.').replace('<p>','').replace('</p>','')
                
                cover_key = comic.get('md_covers', [{}])[0].get('b2key')
                cover_url = f"https://meo.comick.pictures/{cover_key}" if cover_key else ""
                
                author = "Unknown"
                if comic.get('authors'):
                    author = comic['authors'][0].get('name', 'Unknown')
                
                # Fetch Chapters (Try VI, then ALL)
                chap_resp = await client.get(f"{self.base_url}/comic/{hid}/chapters", params={"lang": "vi", "limit": 1000})
                chap_data = chap_resp.json()
                
                chapters = []
                if 'chapters' in chap_data:
                    for chap in chap_data['chapters']:
                        chapters.append({
                            "id": chap['hid'],
                            "title": f"Ch. {chap.get('chap', '?')} - {chap.get('title', '') or ''}",
                            "date": chap.get('created_at', '')[:10]
                        })
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover_url,
                    "rating": float(comic.get('rating', 5.0) or 5.0),
                    "author": author,
                    "description": desc,
                    "chapters": chapters
                }
            except Exception as e:
                print(f"[Comick] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from Comick (chapter_id is hid)"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/chapter/{chapter_id}")
                data = resp.json()
                
                chap = data.get('chapter', {})
                images = chap.get('md_images', [])
                
                pages = []
                for img in images:
                     b2key = img.get('b2key')
                     if b2key:
                         pages.append(f"https://meo.comick.pictures/{b2key}")
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
            except Exception as e:
                print(f"[Comick] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}


# Singleton instance
comick = ComickSource()

# Compatibility wrappers
async def fetch_trending_manga(page=1, limit=18):
    return await comick.fetch_trending(page, limit)

async def fetch_manga_details(manga_id: str):
    return await comick.fetch_manga_details(manga_id)

async def fetch_chapter_pages(chapter_id: str):
    return await comick.fetch_chapter_pages(chapter_id)
