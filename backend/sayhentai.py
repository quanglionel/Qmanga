"""
SayHentai Source - Implementation of BaseSource for sayhentai.net
Note: This is an NSFW source.
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource
import re

class SayHentaiSource(BaseSource):
    """Manga source implementation for SayHentai (NSFW VI)"""
    
    name = "SayHentai"
    language = "VI"
    base_url = "https://sayhentai.net"
    icon = "https://sayhentai.net/favicon.ico"
    is_nsfw = True
    
    async def fetch_trending(self, page: int = 1, limit: int = 50) -> Dict:
        """Fetch latest updates from SayHentai"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/danh-sach?page={page}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                results = []
                # Check for selectors
                items = soup.select('.list-truyen-item') or soup.select('.item-manga')
                
                for item in items:
                    title_el = item.select_one('.title-manga a') or item.select_one('h3 a')
                    if not title_el: continue
                    
                    title = title_el.get_text(strip=True)
                    manga_url = title_el['href']
                    manga_id = manga_url.strip('/').split('/')[-1]
                    
                    img = item.select_one('img')
                    cover = img.get('data-src') or img.get('src') if img else ""
                    if cover and cover.startswith('//'):
                        cover = 'https:' + cover
                    
                    chap_el = item.select_one('.chapter-manga a') or item.select_one('.latest-chapter')
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
                print(f"[SayHentai] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch manga details from SayHentai"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/{manga_id}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title = soup.select_one('.manga-title').get_text(strip=True)
                img = soup.select_one('.manga-cover img')
                cover = img.get('data-src') or img.get('src') if img else ""
                
                author_el = soup.select_one('.author-name')
                author = author_el.get_text(strip=True) if author_el else "Unknown"
                
                desc_el = soup.select_one('.manga-summary')
                description = desc_el.get_text(strip=True) if desc_el else ""
                
                # Chapters
                chapters = []
                chap_items = soup.select('.list-chapters .chapter-item')
                for item in chap_items:
                    link = item.select_one('a')
                    if not link: continue
                    
                    cid = link['href'].strip('/').split('/')[-1]
                    cname = link.select_one('.chapter-name').get_text(strip=True) if link.select_one('.chapter-name') else link.get_text(strip=True)
                    
                    chapters.append({
                        "id": f"{manga_id}/{cid}",
                        "title": cname,
                        "date": ""
                    })
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover,
                    "author": author,
                    "description": description,
                    "chapters": chapters,
                    "source": "sayhentai"
                }
            except Exception as e:
                print(f"[SayHentai] Details Error: {e}")
                return None

    async def fetch_chapter_pages(self, chapter_path: str) -> Dict:
        """Fetch pages for a chapter. chapter_path is 'manga_id/chapter_id'"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/{chapter_path}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                pages = []
                img_items = soup.select('.chapter-content img')
                for img in img_items:
                    purl = img.get('data-src') or img.get('src')
                    if purl:
                        if purl.startswith('//'):
                            purl = 'https:' + purl
                        pages.append(purl)
                
                return {"id": chapter_path, "pages": pages}
            except Exception as e:
                print(f"[SayHentai] Pages Error: {e}")
                return {"id": chapter_path, "pages": []}
