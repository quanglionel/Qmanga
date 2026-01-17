"""
Hentai2Read Source - Manga source (18+ content filtered)
Note: This fetches SFW content only from hentai2read
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
from base_source import BaseSource


class MangakakalotSource(BaseSource):
    """Manga source implementation for Mangakakalot - Popular English manga"""
    
    name = "Mangakakalot"
    language = "EN"
    base_url = "https://mangakakalot.com"
    icon = "https://mangakakalot.com/favicon.ico"
    
    cache_file = "mangakakalot_cache.json"
    CACHE_TTL = 1800
    
    async def fetch_trending(self, page: int = 1, limit: int = 50) -> List[Dict]:
        """Fetch trending manga from Mangakakalot"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                results = []
                
                resp = await client.get(
                    f"{self.base_url}/manga_list",
                    params={"type": "topview", "category": "all", "state": "all", "page": page},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                        "Referer": self.base_url
                    }
                )
                
                if resp.status_code != 200:
                    return {"active_manga": [], "new_manga": []}
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                items = soup.select('.list-truyen-item-wrap, .truyen-list .list-story-item')
                
                for item in items[:limit]:
                    try:
                        link = item.select_one('a')
                        if not link:
                            continue
                        
                        href = link.get('href', '')
                        manga_id = href.split('/')[-1] if '/' in href else href
                        
                        title_el = item.select_one('h3 a, .story_name a')
                        title = title_el.get_text(strip=True) if title_el else link.get('title', 'Unknown')
                        
                        img = item.select_one('img')
                        cover = img.get('src', '') if img else ''
                        
                        chapter_el = item.select_one('.list-story-item-wrap-chapter, .chapter')
                        latest_chapter = chapter_el.get_text(strip=True) if chapter_el else ''
                        
                        results.append({
                            "id": manga_id,
                            "title": title,
                            "cover": cover,
                            "latest_chapter": latest_chapter,
                            "rating": None,
                            "update_time": ""
                        })
                        
                    except Exception:
                        continue
                
                result = {"active_manga": results, "new_manga": []}
                self.save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                print(f"Mangakakalot trending error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Dict:
        """Fetch manga details from Mangakakalot"""
        cache_key = f"details_{manga_id}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                # Try different URL patterns
                urls_to_try = [
                    f"{self.base_url}/manga/{manga_id}",
                    f"{self.base_url}/read-{manga_id}",
                    f"https://chapmanganato.com/manga-{manga_id}"
                ]
                
                soup = None
                for url in urls_to_try:
                    try:
                        resp = await client.get(url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                        })
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            break
                    except:
                        continue
                
                if not soup:
                    return None
                
                title_el = soup.select_one('h1, .manga-info-text h1')
                title = title_el.get_text(strip=True) if title_el else manga_id
                
                cover_el = soup.select_one('.manga-info-pic img, .story-info-left img')
                cover = cover_el.get('src', '') if cover_el else ''
                
                author_el = soup.select_one('.manga-info-text li:contains("Author"), .info-author')
                author = ''
                if author_el:
                    author = author_el.get_text(strip=True).replace('Author(s) :', '').strip()
                
                desc_el = soup.select_one('#noidungm, .panel-story-info-description')
                description = desc_el.get_text(strip=True) if desc_el else ''
                
                chapters = []
                chapter_list = soup.select('.chapter-list .row a, .row-content-chapter li a')
                
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
                
                self.save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                print(f"Mangakakalot details error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> List[str]:
        """Fetch chapter pages from Mangakakalot"""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            try:
                urls_to_try = [
                    f"{self.base_url}/chapter/{chapter_id}",
                    f"https://chapmanganato.com/{chapter_id}"
                ]
                
                for url in urls_to_try:
                    try:
                        resp = await client.get(url, headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                            "Referer": self.base_url
                        })
                        
                        if resp.status_code == 200:
                            soup = BeautifulSoup(resp.text, 'html.parser')
                            
                            pages = []
                            images = soup.select('.container-chapter-reader img, .reading-content img')
                            
                            for img in images:
                                src = img.get('data-src') or img.get('src', '')
                                if src and not src.endswith('.gif'):
                                    pages.append(src)
                            
                            if pages:
                                return pages
                    except:
                        continue
                
                return []
                
            except Exception as e:
                print(f"Mangakakalot pages error: {e}")
                return []
