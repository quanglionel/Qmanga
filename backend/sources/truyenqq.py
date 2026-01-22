import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from .base import BaseSource

# Try to import curl_cffi for Cloudflare bypass
try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False


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

    async def _fetch_html(self, url: str) -> Optional[str]:
        """Fetch HTML with Cloudflare bypass using curl_cffi, fallback to httpx"""
        if HAS_CURL_CFFI:
            try:
                async with AsyncSession(impersonate="chrome120", verify=False) as client:
                    resp = await client.get(url, headers=self.headers, cookies=self.cookies, timeout=25)
                    if resp.status_code == 200:
                        return resp.text
                    print(f"[TruyenQQ] CF Bypass status: {resp.status_code}")
            except Exception as e:
                print(f"[TruyenQQ] curl_cffi error: {e}")
        
        # Fallback to httpx
        try:
            async with httpx.AsyncClient(headers=self.headers, cookies=self.cookies, timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return resp.text
        except Exception as e:
            print(f"[TruyenQQ] httpx error: {e}")
        
        return None


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
        cache_key = f"trending_v3_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        try:
            results = []
            seen_ids = set()
            current_api_page = (page - 1) * 3 + 1
            max_scan_pages = current_api_page + 4
            
            while len(results) < limit and current_api_page <= max_scan_pages:
                url = f"{self.base_url}/truyen-moi-cap-nhat/trang-{current_api_page}.html"
                if current_api_page == 1:
                    url = f"{self.base_url}/truyen-moi-cap-nhat.html"
                
                try:
                    html = await self._fetch_html(url)
                    if not html:
                        break
                        
                    soup = BeautifulSoup(html, 'html.parser')
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
                        
                        manga_id = raw_id.replace('truyen-tranh/', '')
                        
                        if manga_id in seen_ids:
                            continue
                        seen_ids.add(manga_id)
                        
                        imgs = item.select('img')
                        cover_url = ""
                        for img in imgs:
                            src = img.get('src') or img.get('data-src')
                            if not src: continue
                             
                            # Skip decorations
                            if '.svg' in src.lower() or 'icon' in src.lower():
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
                except:
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
        try:
            # Re-add 'truyen-tranh/' if missing, TruyenQQ needs it for the URL
            request_id = manga_id if manga_id.startswith('truyen-tranh/') else f"truyen-tranh/{manga_id}"
            url = f"{self.base_url}/{request_id}"
            
            html = await self._fetch_html(url)
            if not html: return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
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
        try:
            # Re-add 'truyen-tranh/' if missing
            request_id = chapter_id if chapter_id.startswith('truyen-tranh/') else f"truyen-tranh/{chapter_id}"
            url = f"{self.base_url}/{request_id}"
            
            html = await self._fetch_html(url)
            if not html: return {"id": chapter_id, "pages": []}
            
            soup = BeautifulSoup(html, 'html.parser')
            page_els = soup.select('.page-chapter img')
            if not page_els:
                page_els = soup.select('img.lazy')
            if not page_els:
                page_els = soup.select('.reading-detail img')
            
            pages = []
            for img in page_els:
                img_url = img.get('data-src') or img.get('src') or img.get('data-original')
                if img_url:
                    if img_url.startswith('//'): img_url = 'https:' + img_url
                    if 'logo' in img_url.lower() or 'icon' in img_url.lower() or 'notify' in img_url.lower():
                        continue
                    pages.append(img_url)
            
            return {
                "id": chapter_id,
                "pages": pages
            }
        except Exception as e:
            print(f"[TruyenQQ] Pages Error: {e}")
            return {"id": chapter_id, "pages": []}
    async def search(self, query: str, page: int = 1) -> List[Dict]:
        """Search manga on TruyenQQ"""
        q = urllib.parse.quote(query)
        # TruyenQQ search URL: https://truyenqqno.com/tim-kiem/trang-1.html?q=...
        url = f"{self.base_url}/tim-kiem/trang-{page}.html?q={q}"
        
        html = await self._fetch_html(url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.list_grid li')
        
        results = []
        for item in items:
            title_el = item.select_one('.book_name a')
            if not title_el: continue
            
            title = title_el.text.strip()
            href = title_el['href']
            # Normalize ID
            if href.startswith('/'):
                raw_id = href.strip('/')
            else:
                raw_id = href.replace(self.base_url, '').strip('/')
            
            manga_id = raw_id.replace('truyen-tranh/', '')
            
            img_el = item.select_one('img')
            cover_url = ""
            if img_el:
                cover_url = img_el.get('src') or img_el.get('data-src')
                if cover_url and cover_url.startswith('//'):
                    cover_url = 'https:' + cover_url
            
            latest_chap = item.select_one('.last_chapter a')
            chap_text = latest_chap.text.strip() if latest_chap else "N/A"
            
            results.append({
                "id": manga_id,
                "title": title,
                "cover": cover_url,
                "latest_chapter": chap_text,
                "source": "truyenqq"
            })
            
        return results


# Singleton instance
truyenqq = TruyenQQSource()
