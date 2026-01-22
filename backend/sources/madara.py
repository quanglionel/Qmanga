"""
Madara Source - Base implementation for Madara WordPress Theme based sources.
Many manga sites (especially Manhwa/Manhua) use this theme.
"""

import httpx
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Any
from .base import BaseSource
import re
import urllib.parse

class MadaraSource(BaseSource):
    """
    Base source for Madara theme sites.
    Can be inherited or used directly with configuration.
    """
    
    def __init__(self, name: str, base_url: str, lang: str = "VI"):
        self.name = name
        self.base_url = base_url
        self.language = lang
        self.icon = f"{base_url}/favicon.ico"
        self.cache_file = f"{name.lower().replace(' ', '_')}_cache.json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": f"{base_url}/"
        }
        self.load_cache()

    async def fetch_trending(self, page: int = 1, limit: int = 100) -> Dict:
        """Fetch trending/latest updates. Madara usually has ajax load or standard pagination."""
        cache_key = f"trending_{page}_{limit}"
        cached = self.get_from_cache(cache_key)
        if cached: return cached

        try:
            # Common Madara Sort: ?m_orderby=trending or views
            url = f"{self.base_url}/page/{page}/?m_orderby=trending"
            html = await self._fetch_html(url)
            
            # Check for 404/Empty on page loop (some use different pagination structure)
            if not html and page == 1:
                 # Try without page/1/
                 url = f"{self.base_url}/?m_orderby=trending"
                 html = await self._fetch_html(url)

            if not html:
                return {"active_manga": [], "new_manga": []}

            soup = BeautifulSoup(html, 'html.parser')
            results = []
            # Madara item selector
            items = soup.select('.page-item-detail, .c-tabs-item__content')
            
            for item in items:
                title_el = item.select_one('.post-title h3 a, .post-title h4 a, .h5 a')
                if not title_el: continue
                
                title = title_el.text.strip()
                manga_url = title_el['href']
                
                # Extract slug ID
                path = urllib.parse.urlparse(manga_url).path
                manga_id = path.strip('/')
                
                img_el = item.select_one('img')
                cover = ""
                if img_el:
                    cover = img_el.get('data-src') or img_el.get('data-lazy-src') or img_el.get('src')
                    if cover and 'data:image' in cover: 
                        continue
                
                # Chapters
                chap_el = item.select_one('.chapter-item .chapter a')
                latest = chap_el.text.strip() if chap_el else "N/A"
                
                results.append({
                    "id": manga_id,
                    "title": title,
                    "cover": cover,
                    "latest_chapter": latest,
                    "updated_at": ""
                })
            
            # Limit Results locally
            final_res = {
                "active_manga": results[:limit],
                "new_manga": []
            }
            self.set_cache(cache_key, final_res)
            return final_res
            
        except Exception as e:
            print(f"[{self.name}] Trending Error: {e}")
            return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch details. manga_id is usually 'manga/slug' or 'manga-slug'"""
        try:
            url = f"{self.base_url}/{manga_id}"
            html = await self._fetch_html(url)
            if not html: return None
            soup = BeautifulSoup(html, 'html.parser')
            
            # Title
            title_el = soup.select_one('.post-title h1')
            title = title_el.text.strip() if title_el else "Unknown"
            
            # Image
            img_el = soup.select_one('.summary_image img')
            cover = ""
            if img_el:
                cover = img_el.get('data-src') or img_el.get('src')
            
            # Author
            author = "Unknown"
            author_items = soup.select('.post-content_item')
            for item in author_items:
                heading = item.select_one('.summary-heading')
                if heading:
                    h_text = heading.text.lower()
                    if 'author' in h_text or 'tác giả' in h_text:
                         content = item.select_one('.summary-content')
                         if content:
                             author = content.text.strip()
                         break
            
            # Description
            desc_el = soup.select_one('.description-summary .summary__content, .manga-about')
            desc = desc_el.text.strip() if desc_el else ""
            
            # Chapters
            chapters = []
            chap_list = soup.select('.wp-manga-chapter, .chapter-li')
            
            if not chap_list:
                # Try AJAX Load logic
                manga_id_num = soup.select_one('#manga-chapters-holder, .listing-chapters_wrap')
                if manga_id_num and manga_id_num.get('data-id'):
                    post_id = manga_id_num.get('data-id')
                    ajax_url = f"{self.base_url}/wp-admin/admin-ajax.php"
                    
                    form_data = {
                        "action": "manga_get_chapters",
                        "manga": post_id,
                        "manga_id": post_id
                    }
                    ajax_headers = self.headers.copy()
                    ajax_headers["X-Requested-With"] = "XMLHttpRequest"
                    ajax_headers["Referer"] = url
                    
                    ajax_resp_text = await self._fetch_html(ajax_url, method="POST", data=form_data, custom_headers=ajax_headers)
                    if ajax_resp_text:
                         soup_chap = BeautifulSoup(ajax_resp_text, 'html.parser')
                         chap_list = soup_chap.select('.wp-manga-chapter, .chapter-li, li.wp-manga-chapter')

            for li in chap_list:
                a_tag = li.select_one('a')
                if not a_tag: continue
                
                c_url = a_tag['href']
                c_title = a_tag.text.strip()
                c_path = urllib.parse.urlparse(c_url).path.strip('/')
                
                time_el = li.select_one('.chapter-release-date')
                c_date = time_el.text.strip() if time_el else ""
                
                chapters.append({
                    "id": c_path,
                    "title": c_title,
                    "date": c_date
                })
            
            return {
                "id": manga_id,
                "title": title,
                "cover": cover,
                "author": author,
                "description": desc,
                "chapters": chapters,
                "source": self.name.lower()
            }

        except Exception as e:
            print(f"[{self.name}] Details Error: {e}")
            return None

    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages"""
        try:
            url = f"{self.base_url}/{chapter_id}/?style=list"
            html = await self._fetch_html(url)
            if not html: return {"id": chapter_id, "pages": []}
            soup = BeautifulSoup(html, 'html.parser')
            
            pages = []
            imgs = soup.select('.reading-content img, .page-break img')
            for img in imgs:
                src = img.get('data-src') or img.get('src')
                if src:
                    pages.append(src.strip())
            
            return {
                "id": chapter_id,
                "pages": pages
            }
        except Exception as e:
            print(f"[{self.name}] Pages Error: {e}")
            return {"id": chapter_id, "pages": []}
