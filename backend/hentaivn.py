"""
HentaiVN Source - Implementation of BaseSource for hentaivn.moe
Note: This is an NSFW source.
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource
import re

class HentaiVNSource(BaseSource):
    """Manga source implementation for HentaiVN (NSFW VI)"""
    
    name = "HentaiVN"
    language = "VI"
    base_url = "https://hentaivn.ooo" # Mirror that's often stable
    icon = "https://hentaivn.ooo/favicon.ico"
    is_nsfw = True
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://hentaivn.ooo/",
        "Cookie": "check_age=2"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 50) -> Dict:
        """Fetch latest updates from HentaiVN"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}/danh-sach-moi-cap-nhat.html?page={page}"
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                results = []
                items = soup.select('.item')
                
                for item in items:
                    title_el = item.select_one('h2 a')
                    if not title_el: continue
                    
                    title = title_el.get_text(strip=True)
                    manga_url = title_el['href']
                    manga_id = manga_url.split('/')[-1].replace('.html', '')
                    
                    img = item.select_one('img')
                    cover = img.get('data-src') or img.get('src') if img else ""
                    if cover and cover.startswith('//'): cover = 'https:' + cover
                    
                    chap_el = item.select_one('.chapter a')
                    chap_name = chap_el.get_text(strip=True) if chap_el else "Full"
                    
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
                print(f"[HentaiVN] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch details from HentaiVN"""
        # HentaiVN manga_id is usually '12345-title-slug'
        # URL is base_url/manga_id.html
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}/{manga_id}.html"
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title = soup.select_one('.page-title h1').get_text(strip=True)
                img = soup.select_one('.image-manga img')
                cover = img.get('data-src') or img.get('src') if img else ""
                
                info_items = soup.select('.info-item')
                author = "Unknown"
                description = ""
                
                for info in info_items:
                    text = info.get_text()
                    if "Tác giả:" in text:
                        author = info.select_one('a').get_text(strip=True) if info.select_one('a') else "Unknown"
                    if "Nội dung:" in text:
                        description = info.find_next_sibling('div').get_text(strip=True) if info.find_next_sibling('div') else ""

                # Chapters
                chapters = []
                chap_items = soup.select('.list-chapter li')
                for item in chap_items:
                    link = item.select_one('a')
                    if not link: continue
                    
                    cid = link['href'].split('/')[-1].replace('.html', '')
                    cname = link.get_text(strip=True)
                    
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
                    "source": "hentaivn"
                }
            except Exception as e:
                print(f"[HentaiVN] Details Error: {e}")
                return None

    async def fetch_chapter_pages(self, chapter_path: str) -> Dict:
        """Fetch pages. chapter_path is 'manga_slug/chapter_slug'"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                # chapter_path is something like '123-manga/456-chap'
                chap_id = chapter_path.split('/')[-1]
                url = f"{self.base_url}/{chap_id}.html"
                resp = await client.get(url)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                pages = []
                img_items = soup.select('#image img')
                for img in img_items:
                    purl = img.get('src')
                    if purl:
                        if purl.startswith('//'): purl = 'https:' + purl
                        pages.append(purl)
                
                return {"id": chapter_path, "pages": pages}
            except Exception as e:
                print(f"[HentaiVN] Pages Error: {e}")
                return {"id": chapter_path, "pages": []}
