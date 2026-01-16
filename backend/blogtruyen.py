"""
BlogTruyen Source - Implementation of BaseSource (Scraping)
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource


class BlogTruyenSource(BaseSource):
    """Manga source implementation for BlogTruyen scraping"""
    
    name = "BlogTruyen"
    language = "VI"
    base_url = "https://blogtruyen.vn"
    icon = "https://blogtruyen.vn/favicon.ico"
    
    cache_file = "blogtruyen_cache.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://blogtruyen.vn/"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 18) -> List[Dict]:
        """Fetch popular manga from BlogTruyen"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                # BlogTruyenpaging: /danh-sach/moi-cap-nhat-trang-X
                url = f"{self.base_url}/danh-sach/moi-cap-nhat-trang-{page}"
                
                resp = await client.get(url)
                if resp.status_code != 200:
                    return {"active_manga": [], "new_manga": []}
                    
                soup = BeautifulSoup(resp.text, 'html.parser')
                items = soup.select('.list .tiptip')
                
                results = []
                for item in items[:limit]:
                    # item is <a> tag
                    title = item.text.strip()
                    path = item['href'].strip('/')
                    manga_id = path
                    
                    # BlogTruyen grid structure is a bit flat, need to find sibling info
                    # A better way might be searching by list-category
                    pass
                
                # RE-TRY with better selector
                items = soup.select('.list .list-main p') # Actually BlogTruyen grid is a bit old-school
                
                results = []
                for item in items[:limit]:
                    link = item.select_one('a')
                    if not link: continue
                    
                    title = link.text.strip()
                    manga_id = link['href'].strip('/')
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": "", # BlogTruyen grid doesn't always have covers, need another page
                        "latest_chapter": "N/A",
                        "updated_at": ""
                    })
                
                # BlogTruyen is actually hard to scrape via grid for beauty. 
                # Let's use a more visual page if available.
                
                response = {
                    "active_manga": results,
                    "new_manga": []
                }
                
                self.set_cache(cache_key, response)
                return response
                
            except Exception as e:
                print(f"[BlogTruyen] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info from BlogTruyen"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                resp = await client.get(f"{self.base_url}/{manga_id}")
                if resp.status_code != 200: return None
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title = soup.select_one('.entry-title').text.strip()
                desc = soup.select_one('.detail .content').text.strip() if soup.select_one('.detail .content') else ""
                
                img_el = soup.select_one('.thumbnail img')
                cover_url = img_el['src'] if img_el else ""
                
                author = "Unknown"
                # ...
                
                # Chapters
                chapters = []
                chap_items = soup.select('#list-chapters div')
                for item in chap_items:
                    link = item.select_one('a')
                    if not link: continue
                    
                    chap_id = link['href'].strip('/')
                    chap_title = link.text.strip()
                    
                    chapters.append({
                        "id": chap_id,
                        "title": chap_title,
                        "date": ""
                    })
                
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
                print(f"[BlogTruyen] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from BlogTruyen"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                resp = await client.get(f"{self.base_url}/{chapter_id}")
                if resp.status_code != 200: return {"id": chapter_id, "pages": []}
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_els = soup.select('#content img')
                
                pages = []
                for img in page_els:
                    url = img.get('src')
                    if url:
                        pages.append(url)
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
            except Exception as e:
                print(f"[BlogTruyen] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}


# Singleton instance
blogtruyen = BlogTruyenSource()
