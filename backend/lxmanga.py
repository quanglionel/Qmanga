"""
LXManga Source - Implementation of BaseSource for lxmanga.net
Note: This is an NSFW source.
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource
import re

class LXMangaSource(BaseSource):
    """Manga source implementation for LXManga (NSFW VI)"""
    
    name = "LXManga"
    language = "VI"
    base_url = "https://lxmanga.net"
    icon = "https://lxmanga.net/favicon.ico"
    is_nsfw = True
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://lxmanga.net/"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 40) -> Dict:
        """Fetch latest updates from LXManga"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}/danh-sach?page={page}"
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                results = []
                # Grid items usually in .grid
                items = soup.select('.grid .relative.group')
                
                for item in items:
                    title_el = item.select_one('a.truncate')
                    if not title_el: continue
                    
                    title = title_el.get_text(strip=True)
                    manga_url = title_el['href']
                    manga_id = manga_url.strip('/').split('/')[-1]
                    
                    img = item.select_one('img')
                    cover = img.get('src') if img else ""
                    if cover and cover.startswith('//'): cover = 'https:' + cover
                    
                    chap_el = item.select_one('.absolute.bottom-0 a')
                    chap_name = chap_el.get_text(strip=True) if chap_el else "N/A"
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": cover,
                        "latest_chapter": chap_name,
                        "update_time": "Mới"
                    })
                
                return {
                    "active_manga": results,
                    "new_manga": []
                }
            except Exception as e:
                print(f"[LXManga] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch details from LXManga"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}/truyen/{manga_id}"
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title = soup.select_one('h1').get_text(strip=True)
                img = soup.select_one('.flex.flex-col img')
                cover = img.get('src') if img else ""
                
                desc_el = soup.select_one('.description-content') or soup.select_one('.mt-4.text-sm')
                description = desc_el.get_text(strip=True) if desc_el else ""
                
                # Chapters
                chapters = []
                chap_items = soup.select('.overflow-y-auto a')
                for item in chap_items:
                    cid = item['href'].strip('/').split('/')[-1]
                    cname = item.select_one('span').get_text(strip=True) if item.select_one('span') else item.get_text(strip=True)
                    
                    chapters.append({
                        "id": f"{manga_id}/{cid}",
                        "title": cname,
                        "date": ""
                    })
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover,
                    "author": "Unknown",
                    "description": description,
                    "chapters": chapters,
                    "source": "lxmanga"
                }
            except Exception as e:
                print(f"[LXManga] Details Error: {e}")
                return None

    async def fetch_chapter_pages(self, chapter_path: str) -> Dict:
        """Fetch pages for a chapter. chapter_path is 'manga_id/chapter_id'"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                # LXManga chapter URL is base_url/truyen/manga_id/chapter_id
                url = f"{self.base_url}/truyen/{chapter_path}"
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                pages = []
                # Images usually in .chapter-content
                img_items = soup.select('.chapter-content img')
                for img in img_items:
                    purl = img.get('src')
                    if purl:
                        if purl.startswith('//'): purl = 'https:' + purl
                        pages.append(purl)
                
                return {"id": chapter_path, "pages": pages}
            except Exception as e:
                print(f"[LXManga] Pages Error: {e}")
                return {"id": chapter_path, "pages": []}
