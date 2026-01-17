"""
Bato.to Source - Implementation of BaseSource for bato.to
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource
import re

class BatotoSource(BaseSource):
    """Manga source implementation for Bato.to"""
    
    name = "Bato.to"
    language = "Multi"
    base_url = "https://bato.to"
    icon = "https://bato.to/favicon.ico"
    
    async def fetch_trending(self, page: int = 1, limit: int = 50) -> Dict:
        """Fetch latest updates from Bato.to"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Bato filtering for latest
                url = f"{self.base_url}/v7?page={page}"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                results = []
                cards = soup.select('.item') # Check if .item is the right selector for v7
                
                for card in cards:
                    title_el = card.select_one('.item-title')
                    if not title_el: continue
                    
                    manga_id = title_el['href'].split('/')[-1]
                    title = title_el.get_text(strip=True)
                    
                    img = card.select_one('img')
                    cover = img['src'] if img else ""
                    
                    chap_el = card.select_one('.item-volch a')
                    chap_name = chap_el.get_text(strip=True) if chap_el else "N/A"
                    
                    time_el = card.select_one('.item-time')
                    update_time = time_el.get_text(strip=True) if time_el else ""
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": cover,
                        "latest_chapter": chap_name,
                        "update_time": update_time
                    })
                
                return {
                    "active_manga": results,
                    "new_manga": []
                }
            except Exception as e:
                print(f"[Batoto] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch manga details from Bato.to"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/series/{manga_id}"
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title = soup.select_one('.item-title').get_text(strip=True)
                cover = soup.select_one('.attr-item img')['src']
                
                # Check for description
                desc_el = soup.select_one('.limit-html')
                description = desc_el.get_text(strip=True) if desc_el else ""
                
                author = "Unknown"
                author_el = soup.select_one('.attr-item:contains("Author") span, .attr-item:contains("Tác giả") span')
                if author_el:
                    author = author_el.get_text(strip=True)
                
                # Chapters
                chapters = []
                chap_items = soup.select('.main .item')
                for item in chap_items:
                    link = item.select_one('a.chapt')
                    if not link: continue
                    
                    cid = link['href'].split('/')[-1]
                    cname = link.get_text(strip=True)
                    
                    chapters.append({
                        "id": f"{manga_id}/{cid}",
                        "title": cname,
                        "date": "" # Date logic can be added
                    })
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover,
                    "author": author,
                    "description": description,
                    "chapters": chapters,
                    "source": "batoto"
                }
            except Exception as e:
                print(f"[Batoto] Details Error: {e}")
                return None

    async def fetch_chapter_pages(self, chapter_path: str) -> Dict:
        """Fetch pages for a chapter. chapter_path is 'manga_id/chapter_id'"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/chapter/{chapter_path.split('/')[-1]}" # Bato chapters are often standalone IDs
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, headers=headers)
                
                # Bato uses JS to render images, often in a JSON object in a script tag
                # We need to find the script and extract the list
                # Pattern: const images = [...];
                match = re.search(r'const\s+imgHttpLis\s*=\s*(\[.*?\]);', resp.text)
                if not match:
                    # Fallback pattern
                    match = re.search(r'const\s+images\s*=\s*(\[.*?\]);', resp.text)
                
                if match:
                    import json
                    img_urls = json.loads(match.group(1))
                    return {"id": chapter_path, "pages": img_urls}
                
                return {"id": chapter_path, "pages": []}
            except Exception as e:
                print(f"[Batoto] Pages Error: {e}")
                return {"id": chapter_path, "pages": []}
