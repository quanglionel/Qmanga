"""
NetTruyen Source - Implementation of BaseSource (Scraping)
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from base_source import BaseSource


class NetTruyenSource(BaseSource):
    """Manga source implementation for NetTruyen scraping"""
    
    name = "NetTruyen"
    language = "VI"
    base_url = "https://nettruyenar.com"
    icon = "https://nettruyenar.com/favicon.ico"
    
    cache_file = "nettruyen_cache.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://nettruyenar.com/"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch popular manga from NetTruyen with 100 items limit"""
        cache_key = f"trending_v3_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                results = []
                current_api_page = (page - 1) * 3 + 1 # Approximate to get enough
                
                while len(results) < limit and current_api_page < 10:
                    url = self.base_url
                    if current_api_page > 1:
                        url = f"{self.base_url}/trang-{current_api_page}"
                    
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break
                        
                    soup = BeautifulSoup(resp.text, 'html.parser')
                    items = soup.select('.items .item')
                    if not items:
                        break
                        
                    for item in items:
                        title_el = item.select_one('h3 a')
                        if not title_el: continue
                        
                        latest_chap = item.select_one('.comic-item li a') or item.select_one('.chapter a')
                        chap_text = latest_chap.text.strip() if latest_chap else "N/A"
                        
                        # Filter out "Sắp có" (coming soon) 
                        if "sắp có" in chap_text.lower():
                            continue
                            
                        # NetTruyen often shows "Manga" or "Manhua" markers
                        # If we want to avoid B&W, we can check for Manhwa/Manhua labels
                        # But labels are often icons. For now, we load all but provide a way to prioritize.
                        
                        title = title_el.text.strip()
                        href = title_el['href']
                        manga_id = href.replace(self.base_url, '').strip('/')
                        
                        img_el = item.select_one('img')
                        cover_url = ""
                        if img_el:
                             cover_url = img_el.get('data-original') or img_el.get('src')
                             if cover_url and cover_url.startswith('//'):
                                 cover_url = 'https:' + cover_url
                             elif cover_url and not cover_url.startswith('http'):
                                 cover_url = self.base_url.rstrip('/') + '/' + cover_url.lstrip('/')
                        
                        results.append({
                            "id": manga_id,
                            "title": title,
                            "cover": cover_url,
                            "latest_chapter": chap_text,
                            "updated_at": item.select_one('.time').text.strip() if item.select_one('.time') else ""
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
                print(f"[NetTruyen] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info from NetTruyen (manga_id is the path slug)"""
        url = f"{self.base_url}/{manga_id}"
        
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    # Try with trailing slash
                    resp = await client.get(f"{url}/")
                    if resp.status_code != 200: return None
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Robust title selection
                title_tag = soup.select_one('h1.title-detail') or soup.select_one('h1') or soup.select_one('.title')
                title = title_tag.text.strip() if title_tag else "Unknown"
                
                # Description selection
                desc_tag = soup.select_one('.detail-content p') or soup.select_one('.detail-content') or soup.select_one('.description')
                desc = desc_tag.text.strip() if desc_tag else "Chưa có mô tả."
                
                img_el = soup.select_one('.detail-info img') or soup.select_one('.book_avatar img')
                cover_url = ""
                if img_el:
                    cover_url = img_el.get('data-original') or img_el.get('src')
                    if cover_url and cover_url.startswith('//'):
                        cover_url = 'https:' + cover_url
                    elif cover_url and not cover_url.startswith('http'):
                        cover_url = self.base_url.rstrip('/') + '/' + cover_url.lstrip('/')

                author = "Đang cập nhật"
                author_el = soup.select_one('.author p.col-xs-8') or soup.select_one('.author .org')
                if author_el: author = author_el.text.strip()
                
                # Chapters selection
                chapters = []
                chap_items = soup.select('.list-chapter li:not(.heading)')
                if not chap_items:
                    chap_items = soup.select('#list-chapters li')
                
                for item in chap_items:
                    link = item.select_one('a')
                    if not link: continue
                    
                    href = link['href']
                    if href.startswith('http'):
                        chap_id = href.replace(self.base_url, '').strip('/')
                    else:
                        chap_id = href.strip('/')
                        
                    chap_title = link.text.strip()
                    
                    # Date selection
                    date_el = item.select_one('.col-xs-4') or item.select_one('.time') or item.select_one('.date')
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
                print(f"[NetTruyen] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from NetTruyen"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0, follow_redirects=True) as client:
            try:
                url = f"{self.base_url}/{chapter_id}"
                resp = await client.get(url)
                if resp.status_code != 200:
                    # Try with trailing slash
                    resp = await client.get(f"{url}/")
                    if resp.status_code != 200: return {"id": chapter_id, "pages": []}
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                page_els = soup.select('.page-chapter img')
                if not page_els:
                    page_els = soup.select('img[data-original]')
                if not page_els:
                    page_els = soup.select('.reading-detail img')
                
                pages = []
                for img in page_els:
                    url = img.get('data-src') or img.get('data-original') or img.get('src')
                    if url:
                        if url.startswith('//'): url = 'https:' + url
                        elif not url.startswith('http'):
                            url = self.base_url.rstrip('/') + '/' + url.lstrip('/')
                        if 'logo' in url.lower() or 'icon' in url.lower(): continue
                        pages.append(url)
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
            except Exception as e:
                print(f"[NetTruyen] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}



# Singleton instance
nettruyen = NetTruyenSource()
