"""
TruyenQQ Source - Implementation of BaseSource (Scraping)
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import BaseSource


class TruyenQQSource(BaseSource):
    """Manga source implementation for TruyenQQ scraping"""
    
    name = "TruyenQQ"
    language = "VI"
    base_url = "https://truyenqqno.com"
    icon = "https://truyenqqno.com/favicon.ico"
    
    cache_file = "truyenqq_cache.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://truyenqqno.com/"
    }

    def __init__(self):
        super().__init__()
        self.cookies = {}
        self.load_cookies()

    def load_cookies(self):
        try:
            import json
            import os
            cookie_file = "truyenqq_cookies.json"
            if os.path.exists(cookie_file):
                with open(cookie_file, 'r') as f:
                    self.cookies = json.load(f)
                print(f"[TruyenQQ] Loaded cookies from {cookie_file}")
        except Exception as e:
            print(f"[TruyenQQ] Failed to load cookies: {e}")

    
    async def fetch_trending(self, page: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch popular manga from TruyenQQ with 100 items limit"""
        cache_key = f"trending_v2_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        async with httpx.AsyncClient(headers=self.headers, cookies=self.cookies, timeout=30.0, follow_redirects=True) as client:
            try:
                results = []
                current_api_page = (page - 1) * 3 + 1
                
                while len(results) < limit and current_api_page < 10:
                    url = f"{self.base_url}/truyen-moi-cap-nhat/trang-{current_api_page}.html"
                    if current_api_page == 1:
                        url = f"{self.base_url}/truyen-moi-cap-nhat.html"
                    
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break
                        
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    items = soup.select('.list_grid li')
                    if not items:
                        break
                        
                    for item in items:
                        title_el = item.select_one('.book_name a')
                        if not title_el: continue
                        
                        title = title_el.text.strip()
                        href = title_el['href']
                        if href.startswith('/'):
                            raw_id = href.strip('/')
                        else:
                            raw_id = href.replace(self.base_url, '').strip('/')
                        
                        # Remove 'truyen-tranh/' prefix if present to normalize IDs
                        manga_id = raw_id.replace('truyen-tranh/', '')
                        
                        imgs = item.select('img')
                        cover_url = ""
                        for img in imgs:
                            src = img.get('src') or img.get('data-src')
                            if not src: continue
                             
                            # Skip decoration/holiday images
                            classes = img.get('class', [])
                            if not isinstance(classes, list): classes = [str(classes)]
                            
                            # Check classes
                            if 'holiday-ui-wrapper' in classes or any('holiday' in c for c in classes):
                                continue
                                
                            # Check src content
                            src_lower = src.lower()
                            if 'cloud' in src_lower or 'tet' in src_lower or 'icon' in src_lower:
                                continue
                                
                            # Check alt text
                            alt = img.get('alt', '').lower()
                            if 'cloud' in alt:
                                continue

                            # Skip SVGs (decorations)
                            if '.svg' in src_lower:
                                continue
                                
                            cover_url = src
                            if cover_url.startswith('//'):
                                cover_url = 'https:' + cover_url
                            elif not cover_url.startswith('http'):
                                cover_url = self.base_url.rstrip('/') + '/' + cover_url.lstrip('/')
                            break
                        
                        latest_chap = item.select_one('.last_chapter a')
                        chap_text = latest_chap.text.strip() if latest_chap else "N/A"
                        
                        results.append({
                            "id": manga_id,
                            "title": title,
                            "cover": cover_url,
                            "latest_chapter": chap_text,
                            "updated_at": "" 
                        })
                        
                        if len(results) >= limit:
                            break
                    
                    current_api_page += 1
                
                response = {
                    "active_manga": results[:limit],
                    "new_manga": []
                }
                
                self.set_cache(cache_key, response)
                return response
                
            except Exception as e:
                print(f"[TruyenQQ] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info from TruyenQQ"""
        async with httpx.AsyncClient(headers=self.headers, cookies=self.cookies, timeout=30.0, follow_redirects=True) as client:
            try:
                # Re-add 'truyen-tranh/' if missing, TruyenQQ needs it for the URL
                request_id = manga_id if manga_id.startswith('truyen-tranh/') else f"truyen-tranh/{manga_id}"
                url = f"{self.base_url}/{request_id}"
                resp = await client.get(url)
                if resp.status_code != 200: return None
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title_el = soup.select_one('h1')
                title = title_el.text.strip() if title_el else "Unknown"
                
                desc_el = soup.select_one('.detail-content p') or soup.select_one('.detail-content')
                desc = desc_el.text.strip() if desc_el else "Chưa có mô tả."
                
                img_el = soup.select_one('.book_avatar img')
                cover_url = ""
                if img_el:
                    cover_url = img_el.get('src') or img_el.get('data-src')
                    if cover_url and cover_url.startswith('//'):
                        cover_url = 'https:' + cover_url
                
                author = "Unknown"
                author_el = soup.select_one('.author .org') or soup.select_one('.author p.col-xs-8')
                if author_el: author = author_el.text.strip()
                
                # Chapters
                chapters = []
                chap_items = soup.select('.works-chapter-item')
                for item in chap_items:
                    link = item.select_one('a')
                    if not link: continue
                    
                    href = link['href']
                    if href.startswith('/'):
                        raw_chap_id = href.strip('/')
                    else:
                        raw_chap_id = href.replace(self.base_url, '').strip('/')
                    
                    chap_id = raw_chap_id.replace('truyen-tranh/', '')
                        
                    chap_title = link.text.strip()
                    date_el = item.select_one('.time-chap')
                    chap_date = date_el.text.strip() if date_el else ""
                    
                    chapters.append({
                        "id": chap_id,
                        "title": chap_title,
                        "date": chap_date
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
                print(f"[TruyenQQ] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from TruyenQQ"""
        async with httpx.AsyncClient(headers=self.headers, cookies=self.cookies, timeout=30.0, follow_redirects=True) as client:
            try:
                # Re-add 'truyen-tranh/' if missing
                request_id = chapter_id if chapter_id.startswith('truyen-tranh/') else f"truyen-tranh/{chapter_id}"
                url = f"{self.base_url}/{request_id}"
                resp = await client.get(url)
                if resp.status_code != 200: return {"id": chapter_id, "pages": []}
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_els = soup.select('.page-chapter img')
                if not page_els:
                    page_els = soup.select('img.lazy')
                if not page_els:
                    page_els = soup.select('.reading-detail img')
                
                pages = []
                for img in page_els:
                    url = img.get('data-src') or img.get('src') or img.get('data-original')
                    if url:
                        if url.startswith('//'): url = 'https:' + url
                        if 'logo' in url.lower() or 'icon' in url.lower() or 'notify' in url.lower():
                            continue
                        pages.append(url)
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
            except Exception as e:
                print(f"[TruyenQQ] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}



# Singleton instance
truyenqq = TruyenQQSource()
