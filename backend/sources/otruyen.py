"""
Otruyen Source - Implementation of BaseSource for otruyenapi.com
"""

import httpx
import asyncio
from typing import List, Dict, Optional
from .base import BaseSource


class OtruyenSource(BaseSource):
    """Manga source implementation for Otruyen API"""
    
    name = "Otruyen"
    language = "VI"
    base_url = "https://otruyenapi.com/v1/api"
    img_base = "https://img.otruyenapi.com/uploads/comics"
    icon = "https://otruyenapi.com/favicon.ico"
    
    cache_file = "otruyen_cache.json"
    CACHE_TTL = 3600  # 1 hour
    
    async def fetch_trending(self, page: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch trending/latest manga from Otruyen with 100 items limit and B&W filtering"""
        # Page in our API vs API pages might differ if we want 100 at once
        # For simplicity, if limit is 100, we fetch multiple API pages
        cache_key = f"trending_v2_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                results = []
                api_page = (page - 1) * 4 + 1 # Attempt to get enough items
                
                # Fetch multiple pages until we hit the limit or run out
                while len(results) < limit and api_page < 10: 
                    resp = await client.get(
                        f"{self.base_url}/danh-sach/truyen-moi",
                        params={"page": api_page}
                    )
                    if resp.status_code != 200:
                        break
                        
                    data = resp.json()
                    items = data.get('data', {}).get('items', [])
                    if not items:
                        break
                        
                    for item in items:
                        # Otruyen items have category list
                        categories = [c.get('name', '').lower() for c in item.get('category', [])]
                        
                        # FILTER: Skip Manga (often B&W) and Adult content
                        is_bw = "manga" in categories
                        is_adult = any(x in categories for x in ["18+", "adult", "smut", "ecchi", "hentai"])
                        
                        if is_bw or is_adult:
                            continue
                            
                        # SKIP: Manga with no chapters yet
                        chapters = item.get('chaptersLatest')
                        if not chapters:
                            continue
                            
                        slug = item.get('slug')
                        cover_path = item.get('thumb_url', '')
                        if 'uploads/comics' not in cover_path:
                            cover_url = f"{self.img_base}/{cover_path}"
                        else:
                            cover_url = f"{self.img_base.replace('/uploads/comics','')}/{cover_path}"
                            
                        # Use last item in chapters for latest chapter display (fast approximation)
                        latest_chap = f"Ch. {chapters[0].get('chapter_name', '?')}" if chapters else "N/A"

                        results.append({
                            "id": slug,
                            "title": item.get('name'),
                            "cover": cover_url,
                            "rating": 5.0,
                            "latest_chapter": latest_chap,
                            "updated_at": item.get('updatedAt', '')
                        })
                        
                        if len(results) >= limit:
                            break
                    
                    api_page += 1
                
                final_data = {
                    "active_manga": results[:limit],
                    "new_manga": []
                }
                
                self.set_cache(cache_key, final_data)
                return final_data
                
            except Exception as e:
                print(f"[Otruyen] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info for a specific manga"""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/truyen-tranh/{manga_id}")
                data = resp.json()
                
                item = data.get('data', {}).get('item', {})
                if not item:
                    return None
                
                base_img = data.get('data', {}).get('APP_DOMAIN_CDN_IMAGE', self.img_base)
                
                title = item.get('name')
                desc = item.get('content', 'Chưa có mô tả.').replace('<p>','').replace('</p>','')
                cover_path = item.get('thumb_url', '')
                
                if 'uploads/comics' not in base_img and 'uploads/comics' not in cover_path:
                    cover_url = f"{base_img}/uploads/comics/{cover_path}"
                else:
                    cover_url = f"{base_img}/{cover_path}"
                
                author = item.get('author', ['Unknown'])[0] if isinstance(item.get('author'), list) else 'Unknown'
                
                # Build chapters list
                chapters = []
                server_list = item.get('chapters', [])
                if server_list:
                    for server in server_list:
                        server_chapters = server.get('server_data', [])
                        for chap in server_chapters:
                            full_title = f"Chương {chap.get('chapter_name', '?')}"
                            if chap.get('chapter_title'):
                                full_title += f" - {chap.get('chapter_title')}"
                            
                            api_link = chap.get('chapter_api_data') or chap.get('api_data')
                            if api_link:
                                chapters.append({
                                    "id": api_link,
                                    "title": full_title,
                                    "date": "N/A"
                                })
                
                # Reverse to show newest first
                chapters.reverse()
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover_url,
                    "rating": 5.0,
                    "author": author,
                    "description": desc,
                    "chapters": chapters
                }
                
            except Exception as e:
                print(f"[Otruyen] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a specific chapter"""
        # Fix collapsed slashes if they occur during routing (e.g. https:/ -> https://)
        if chapter_id.startswith('http:/') and not chapter_id.startswith('http://'):
            chapter_id = chapter_id.replace('http:/', 'http://', 1)
        elif chapter_id.startswith('https:/') and not chapter_id.startswith('https://'):
            chapter_id = chapter_id.replace('https:/', 'https://', 1)
            
        async with httpx.AsyncClient() as client:
            try:
                print(f"[Otruyen] Fetching Chapter API: {chapter_id}")
                resp = await client.get(chapter_id)  # chapter_id is the full API URL
                print(f"[Otruyen] Chapter API Status: {resp.status_code}")
                data = resp.json()
                
                item = data.get('data', {}).get('item', {})
                domain_cdn = data.get('data', {}).get('domain_cdn', '')
                chapter_path = item.get('chapter_path', '')
                images = item.get('chapter_image', [])
                
                pages = []
                # Ensure domain_cdn doesn't have trailing slash and path has leading segment
                cdn = domain_cdn.rstrip('/')
                for img_file in images:
                    file_name = img_file.get('image_file')
                    path = chapter_path.strip('/')
                    full_url = f"{cdn}/{path}/{file_name}"
                    pages.append(full_url)
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
                
            except Exception as e:
                print(f"[Otruyen] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}


# Create singleton instance for easy import
otruyen = OtruyenSource()

# Legacy function wrappers for backward compatibility
async def fetch_trending_manga(page=1, limit=18):
    return await otruyen.fetch_trending(page, limit)

async def fetch_manga_details(manga_id: str):
    return await otruyen.fetch_manga_details(manga_id)

async def fetch_chapter_pages(chapter_url: str):
    return await otruyen.fetch_chapter_pages(chapter_url)
