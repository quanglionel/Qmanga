"""
NHentai Source - Implementation of BaseSource for nhentai.net
Note: This is an NSFW source.
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource
import re

class NHentaiSource(BaseSource):
    """Manga source implementation for NHentai (NSFW Multi)"""
    
    name = "NHentai"
    language = "Multi"
    base_url = "https://nhentai.net"
    icon = "https://nhentai.net/favicon.ico"
    is_nsfw = True
    
    async def fetch_trending(self, page: int = 1, limit: int = 25) -> Dict:
        """Fetch latest uploads from NHentai"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/?page={page}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                results = []
                # Gallery items
                galleries = soup.select('.gallery')
                
                for gal in galleries:
                    link = gal.select_one('a')
                    if not link: continue
                    
                    manga_id = link['href'].strip('/').split('/')[-1]
                    title_el = gal.select_one('.caption')
                    title = title_el.get_text(strip=True) if title_el else "Gallery " + manga_id
                    
                    img = gal.select_one('img')
                    cover = img.get('data-src') or img.get('src') if img else ""
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": cover,
                        "latest_chapter": "Full",
                        "update_time": "Mới"
                    })
                
                return {
                    "active_manga": results,
                    "new_manga": []
                }
            except Exception as e:
                print(f"[NHentai] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch gallery details from NHentai"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/g/{manga_id}/"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title_pretty = soup.select_one('#info h1.title .pretty')
                title = title_pretty.get_text(strip=True) if title_pretty else soup.select_one('#info h1.title').get_text(strip=True)
                
                cover_img = soup.select_one('#cover img')
                cover = cover_img.get('data-src') or cover_img.get('src')
                
                # Tags as tags/genres
                tags = [a.select_one('.name').get_text(strip=True) for a in soup.select('.tag-container:contains("Tags") a')]
                
                # NHentai single "chapter" is the whole gallery
                chapters = [{
                    "id": f"{manga_id}/1",
                    "title": "Full Gallery",
                    "date": ""
                }]
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover,
                    "author": "Various",
                    "description": ", ".join(tags),
                    "chapters": chapters,
                    "source": "nhentai"
                }
            except Exception as e:
                print(f"[NHentai] Details Error: {e}")
                return None

    async def fetch_chapter_pages(self, chapter_path: str) -> Dict:
        """Fetch pages for an NHentai gallery. NHentai uses a media server."""
        manga_id = chapter_path.split('/')[0]
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/g/{manga_id}/"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Find the gallery meta data in script or just scrape thumb links
                # Usually thumbs are: https://t.nhentai.net/galleries/MEDIA_ID/1t.jpg
                # Images are: https://i.nhentai.net/galleries/MEDIA_ID/1.jpg
                
                # Extract media_id from cover url
                cover_img = soup.select_one('#cover img')
                cover_src = cover_img.get('data-src') or cover_img.get('src')
                media_match = re.search(r'/galleries/(\d+)/', cover_src)
                if not media_match: return {"id": chapter_path, "pages": []}
                
                media_id = media_match.group(1)
                
                # Count total pages
                num_pages_el = soup.select_one('#info div:contains("pages")')
                if not num_pages_el:
                    num_pages_el = soup.find(string=re.compile(r'\d+\s+pages'))
                
                num_pages = 0
                if num_pages_el:
                    num_text = num_pages_el.get_text() if hasattr(num_pages_el, 'get_text') else str(num_pages_el)
                    p_match = re.search(r'(\d+)', num_text)
                    if p_match: num_pages = int(p_match.group(1))
                
                # Detect image extension from thumbs
                first_thumb = soup.select_one('.thumb-container img')
                ext = "jpg"
                if first_thumb:
                    t_src = first_thumb.get('data-src') or first_thumb.get('src')
                    if ".png" in t_src: ext = "png"
                    elif ".webp" in t_src: ext = "webp"
                
                pages = [f"https://i.nhentai.net/galleries/{media_id}/{i}.{ext}" for i in range(1, num_pages + 1)]
                
                return {"id": chapter_path, "pages": pages}
            except Exception as e:
                print(f"[NHentai] Pages Error: {e}")
                return {"id": chapter_path, "pages": []}
