"""
Manhwatop Source - Korean Manhwa in Vietnamese
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
from base_source import BaseSource


class ManhwatopSource(BaseSource):
    """Manga source implementation for Manhwatop"""
    
    name = "Manhwatop"
    language = "VI"
    base_url = "https://manhwatop.net"
    icon = "https://manhwatop.net/favicon.ico"
    
    cache_file = "manhwatop_cache.json"
    CACHE_TTL = 1800
    
    async def fetch_trending(self, page: int = 1, limit: int = 50) -> List[Dict]:
        """Fetch trending manga from Manhwatop"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                results = []
                
                for p in range(page, page + 3):  # Fetch 3 pages
                    resp = await client.get(
                        f"{self.base_url}/tim-truyen",
                        params={"page": p, "sort": "update"},
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": self.base_url
                        }
                    )
                    
                    if resp.status_code != 200:
                        break
                    
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    
                    items = soup.select('.list-truyen .item, .items .item')
                    if not items:
                        break
                    
                    for item in items:
                        try:
                            link = item.select_one('a')
                            if not link:
                                continue
                            
                            href = link.get('href', '')
                            manga_id = href.split('/')[-1] if '/' in href else href
                            
                            title_el = item.select_one('.name, h3 a, .title')
                            title = title_el.get_text(strip=True) if title_el else 'Unknown'
                            
                            img = item.select_one('img')
                            cover = ''
                            if img:
                                cover = img.get('data-src') or img.get('data-original') or img.get('src', '')
                                if cover and not cover.startswith('http'):
                                    cover = self.base_url + cover
                            
                            chapter_el = item.select_one('.chapter a, .chapter-name')
                            latest_chapter = chapter_el.get_text(strip=True) if chapter_el else ''
                            
                            results.append({
                                "id": manga_id,
                                "title": title,
                                "cover": cover,
                                "latest_chapter": latest_chapter,
                                "rating": None,
                                "update_time": ""
                            })
                            
                            if len(results) >= limit:
                                break
                                
                        except Exception as e:
                            continue
                    
                    if len(results) >= limit:
                        break
                
                result = {"active_manga": results[:limit], "new_manga": []}
                self.set_cache(cache_key, result)
                return result
                
            except Exception as e:
                print(f"Manhwatop trending error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Dict:
        """Fetch manga details from Manhwatop"""
        cache_key = f"details_{manga_id}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/truyen/{manga_id}"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": self.base_url
                })
                
                if resp.status_code != 200:
                    return None
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                title_el = soup.select_one('h1.title, .title-detail')
                title = title_el.get_text(strip=True) if title_el else manga_id
                
                cover_el = soup.select_one('.thumb img, .detail-info img')
                cover = ''
                if cover_el:
                    cover = cover_el.get('data-src') or cover_el.get('src', '')
                    if cover and not cover.startswith('http'):
                        cover = self.base_url + cover
                
                author_el = soup.select_one('.author, .info-author')
                author = author_el.get_text(strip=True) if author_el else ''
                
                desc_el = soup.select_one('.detail-content, .description')
                description = desc_el.get_text(strip=True) if desc_el else ''
                
                chapters = []
                chapter_list = soup.select('.list-chapter li a, #nt_listchapter li a')
                
                for ch in chapter_list:
                    ch_href = ch.get('href', '')
                    ch_id = ch_href.split('/')[-1] if ch_href else ''
                    ch_title = ch.get_text(strip=True)
                    
                    chapters.append({
                        "id": ch_id,
                        "title": ch_title,
                        "date": ""
                    })
                
                result = {
                    "id": manga_id,
                    "title": title,
                    "cover": cover,
                    "author": author,
                    "description": description,
                    "chapters": chapters,
                    "rating": None
                }
                
                self.set_cache(cache_key, result)
                return result
                
            except Exception as e:
                print(f"Manhwatop details error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> List[str]:
        """Fetch chapter pages from Manhwatop"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                url = f"{self.base_url}/truyen/{chapter_id}"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": self.base_url
                })
                
                if resp.status_code != 200:
                    return []
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                pages = []
                images = soup.select('.reading-content img, .page-chapter img, #image img')
                
                for img in images:
                    src = img.get('data-src') or img.get('data-original') or img.get('src', '')
                    if src and 'loading' not in src.lower():
                        if not src.startswith('http'):
                            src = self.base_url + src
                        pages.append(src)
                
                return pages
                
            except Exception as e:
                print(f"Manhwatop pages error: {e}")
                return []
