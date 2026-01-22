"""
NetTruyen Source - Implementation of BaseSource (Scraping)
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import urllib.parse
from .base import BaseSource

class NetTruyenSource(BaseSource):
    """Manga source implementation for NetTruyen scraping"""
    
    name = "NetTruyen"
    language = "VI"
    base_url = "https://nettruyen.best" 
    icon = "https://nettruyen.best/favicon.ico"
    
    cache_file = "nettruyen_cache.json"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://nettruyen.best/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # Backup domains
    extra_domains = [
        "https://nettruyennew.com",
        "https://nettruyenbb.com",
        "https://nettruyenvv.com",
        "https://nettruyentv.com",
        "https://nettruyenco.vn",
        "https://nettruyenrr.com",
        "https://nettruyenx.com",
        "https://nettruyenww.com",
        "https://nettruyenin.com",
        "https://nettruyentop.com"
    ]
    
    item_selector = ".items .item"

    
    async def fetch_trending(self, page: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch popular manga from NetTruyen with 100 items limit"""
        cache_key = f"trending_v5_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        # Domain rotation list if primary fails
        domains = [self.base_url] + self.extra_domains
        
        try:
            results = []
            current_api_page = (page - 1) * 3 + 1
            
            # List of domains to try
            all_possible_domains = [self.base_url] + self.extra_domains
            valid_html = None
            working_domain = self.base_url

            print(f"[{self.name}] Đang thử tìm tên miền hoạt động trong: {all_possible_domains}")
            
            for dom in all_possible_domains:
                dom = dom.rstrip('/')
                test_url = dom if current_api_page == 1 else f"{dom}/trang-{current_api_page}"
                
                # CRITICAL: Match Referer to current domain
                test_headers = self.headers.copy()
                test_headers["Referer"] = f"{dom}/"
                
                html = await self._fetch_html(test_url, custom_headers=test_headers)
                if html and ("NetTruyen" in html or "items" in html):
                    valid_html = html
                    working_domain = dom
                    self.base_url = dom 
                    self.headers["Referer"] = f"{dom}/"
                    print(f"[{self.name}] KẾT NỐI THÀNH CÔNG: {dom}")
                    break
                else:
                    print(f"[{self.name}] Tên miền {dom} bị chặn (403) hoặc không có dữ liệu.")

            if not valid_html:
                print(f"[{self.name}] TẤT CẢ các tên miền đều bị chặn bởi Cloudflare.")
                return {"active_manga": [], "new_manga": []}

            seen_ids = set()
            max_scan_pages = current_api_page + 2
            
            # Use the already fetched valid_html for the first page
            current_html = valid_html
            
            while len(results) < limit and current_api_page <= max_scan_pages:
                if not current_html:
                    url = working_domain
                    if current_api_page > 1:
                        url = f"{working_domain}/trang-{current_api_page}"
                    
                    try:
                        # Use updated Referer
                        test_headers = self.headers.copy()
                        test_headers["Referer"] = f"{working_domain}/"
                        current_html = await self._fetch_html(url, custom_headers=test_headers)
                        if not current_html:
                            break
                    except:
                        break
                
                soup = BeautifulSoup(current_html, 'html.parser')
                items = soup.select(self.item_selector) or soup.select('.item')
                if not items:
                    break
                        
                for item in items:
                    title_el = item.select_one('h3 a')
                    if not title_el: continue
                    
                    latest_chap = item.select_one('.comic-item li a') or item.select_one('.chapter a')
                    chap_text = latest_chap.text.strip() if latest_chap else "N/A"
                    
                    if "sắp có" in chap_text.lower():
                        continue
                        
                    title = title_el.text.strip()
                    href = title_el['href']
                    parsed_href = urllib.parse.urlparse(href)
                    manga_id = parsed_href.path.strip('/')
                    
                    if manga_id in seen_ids:
                        continue
                    seen_ids.add(manga_id)
                    
                    img_el = item.select_one('img')
                    cover_url = ""
                    if img_el:
                         cover_url = img_el.get('data-original') or img_el.get('src')
                         if cover_url and cover_url.startswith('//'):
                             cover_url = 'https:' + cover_url
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": cover_url,
                        "latest_chapter": chap_text,
                        "updated_at": item.select_one('.time').text.strip() if item.select_one('.time') else ""
                    })
                    
                    if len(results) >= limit:
                        break
                
                # Reset for next page
                current_html = None
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
        
        try:
            html = await self._fetch_html(url)
            if not html:
                # Try with trailing slash
                html = await self._fetch_html(f"{url}/")
            if not html:
                return None
            
            soup = BeautifulSoup(html, 'html.parser')
            
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
                # Robust ID extraction: get path only
                parsed_href = urllib.parse.urlparse(href)
                chap_id = parsed_href.path.strip('/')
                    
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
        try:
            url = f"{self.base_url}/{chapter_id}"
            if chapter_id.startswith('http'): url = chapter_id

            html = await self._fetch_html(url)
            if not html:
                # Try with trailing slash
                html = await self._fetch_html(f"{url}/")
            if not html:
                return {"id": chapter_id, "pages": []}
            
            soup = BeautifulSoup(html, 'html.parser')
            page_els = soup.select('.page-chapter img')
            if not page_els:
                page_els = soup.select('img[data-original]')
            if not page_els:
                page_els = soup.select('.reading-detail img')
            
            pages = []
            for img in page_els:
                img_url = img.get('data-src') or img.get('data-original') or img.get('src')
                if img_url:
                    if img_url.startswith('//'): img_url = 'https:' + img_url
                    elif not img_url.startswith('http'):
                        img_url = self.base_url.rstrip('/') + '/' + img_url.lstrip('/')
                    if 'logo' in img_url.lower() or 'icon' in img_url.lower(): continue
                    pages.append(img_url)
            
            return {
                "id": chapter_id,
                "pages": pages
            }
        except Exception as e:
            print(f"[NetTruyen] Pages Error: {e}")
            return {"id": chapter_id, "pages": []}
    async def search(self, query: str, page: int = 1) -> List[Dict]:
        """Search manga on NetTruyen"""
        q = urllib.parse.quote(query)
        url = f"{self.base_url}/tim-truyen?keyword={q}&page={page}"
        
        html = await self._fetch_html(url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select(self.item_selector) or soup.select('.item')
        
        results = []
        for item in items:
            title_el = item.select_one('h3 a')
            if not title_el: continue
            
            title = title_el.text.strip()
            href = title_el['href']
            parsed_href = urllib.parse.urlparse(href)
            manga_id = parsed_href.path.strip('/')
            
            img_el = item.select_one('img')
            cover_url = ""
            if img_el:
                 cover_url = img_el.get('data-original') or img_el.get('src')
                 if cover_url and cover_url.startswith('//'):
                     cover_url = 'https:' + cover_url
                 elif cover_url and not cover_url.startswith('http'):
                     cover_url = self.base_url.rstrip('/') + '/' + cover_url.lstrip('/')
            
            latest_chap = item.select_one('.chapter a')
            chap_text = latest_chap.text.strip() if latest_chap else "N/A"
            
            results.append({
                "id": manga_id,
                "title": title,
                "cover": cover_url,
                "latest_chapter": chap_text,
                "source": "nettruyen"
            })
            
        return results


# Singleton instance
nettruyen = NetTruyenSource()
