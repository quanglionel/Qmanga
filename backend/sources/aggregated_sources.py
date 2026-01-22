"""
Aggregated sources that use common structures (NetTruyen, TruyenQQ, etc.)
"""

from .nettruyen import NetTruyenSource
from .madara import MadaraSource
from .base import BaseSource
import httpx
from bs4 import BeautifulSoup
import urllib.parse
from typing import List, Dict, Optional
try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False

import subprocess
import shutil

class CurlWrapper:
    @staticmethod
    def get_sync(url):
        curl_path = shutil.which("curl")
        if not curl_path: return None
        try:
             # -s for silent, but we need body. 
             # curl outputs body to stdout by default.
            cmd = [curl_path, "-s", "-L", "-H", "User-Agent: Mozilla/5.0", url]
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
            return res.stdout
        except Exception as e:
            print(f"Curl Error: {e}")
            return None

    @staticmethod
    async def get(url):
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, CurlWrapper.get_sync, url)

class GenericNettruyenSource(NetTruyenSource):
    """A helper to quickly add NetTruyen clones"""
    def __init__(self, name, base_url, icon=None):
        super().__init__()
        self.name = name
        self.base_url = base_url
        self.icon = icon or f"{base_url}/favicon.ico"
        self.cache_file = f"{name.lower().replace(' ', '_')}_cache.json"
        self.headers["Referer"] = f"{base_url}/"
        self.extra_domains = [] # Don't use NetTruyen backups for clones



class DocTruyen3QSource(GenericNettruyenSource):
    item_selector = ".item-manga .item"

# SFW Sources
doctruyen3q = DocTruyen3QSource("DocTruyen3Q", "https://doctruyen3qhubz.com")
truyentranh3q = GenericNettruyenSource("TruyenTranh3Q", "https://truyentranh3qk.com")
toptruyen = GenericNettruyenSource("TopTruyen", "https://www.toptruyentv15.com")
nettruyenco = GenericNettruyenSource("NetTruyen", "https://nettruyenar.com")
nettruyenx = GenericNettruyenSource("NetTruyenX", "https://nettruyenx.net")
class DocTruyen5SSource(BaseSource):
    """Specialized source for DocTruyen5S (manga.io.vn)"""
    def __init__(self):
        super().__init__()
        self.name = "DocTruyen5S"
        self.base_url = "https://manga.io.vn"
        self.icon = "https://manga.io.vn/favicon.ico"
        self.cache_file = "doctruyen5s_cache.json"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://manga.io.vn/"
        }

    async def fetch_trending(self, page: int = 1, limit: int = 30) -> Dict:
        cache_key = f"trending_v1_{page}_{limit}"
        cached = self.get_from_cache(cache_key)
        if cached: return cached

        # Try curl_cffi first
        html = None
        if HAS_CURL_CFFI:
            try:
                async with AsyncSession(headers=self.headers, impersonate="chrome120", verify=False) as client:
                    url = self.base_url
                    if page > 1: url = f"{self.base_url}/danh-sach-truyen?page={page}"
                    resp = await client.get(url, timeout=20)
                    if resp.status_code == 200:
                        html = resp.text
            except Exception as e:
                print(f"[{self.name}] Cffi Error: {e}")
        
        # Fallback to system curl
        if not html:
            print(f"[{self.name}] Falling back to system curl...")
            url = self.base_url if page == 1 else f"{self.base_url}/danh-sach-truyen?page={page}"
            html = await CurlWrapper.get(url)
        
        if not html:
             return {"active_manga": [], "new_manga": []}
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.select('#home-tab-update > div') or soup.select('.grid > div')
            
            results = []
            for item in items:
                title_el = item.select_one('.text-center a')
                if not title_el: continue
                
                href = title_el['href']
                parsed_href = urllib.parse.urlparse(href)
                manga_id = parsed_href.path.strip('/')
                
                img_el = item.select_one('img')
                cover_url = ""
                if img_el:
                    cover_url = img_el.get('data-src') or img_el.get('src')
                    if cover_url and not cover_url.startswith('http'):
                        cover_url = self.base_url.rstrip('/') + '/' + cover_url.lstrip('/')
                
                # Latest chapter is usually a sibling anchor
                chap_el = item.select_one('a[href*="/chapter-"]')
                chap_text = chap_el.text.strip() if chap_el else "N/A"
                
                results.append({
                    "id": manga_id,
                    "title": title_el.text.strip(),
                    "cover": cover_url,
                    "latest_chapter": chap_text,
                    "updated_at": ""
                })
                if len(results) >= limit: break
            
            res = {"active_manga": results, "new_manga": []}
            self.set_cache(cache_key, res)
            return res
        except Exception as e:
            print(f"[{self.name}] Parse Error: {e}")
            return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        url = f"{self.base_url}/{manga_id}"
        html = None
        if HAS_CURL_CFFI:
            try:
                async with AsyncSession(headers=self.headers, impersonate="chrome120", verify=False) as client:
                    resp = await client.get(url, timeout=20)
                    if resp.status_code == 200: html = resp.text
            except: pass
        
        if not html:
            html = await CurlWrapper.get(url)
            
        if not html: return None

        try:
            soup = BeautifulSoup(html, 'html.parser')
            title_tag = soup.select_one('h1')
            if not title_tag: return None
            
            desc_tag = soup.select_one('#syn-target')
            desc = desc_tag.text.strip() if desc_tag else "Chưa có mô tả."
            
            img_el = soup.select_one('.md-auto img')
            cover_url = img_el['src'] if img_el else ""
            if cover_url and not cover_url.startswith('http'):
                cover_url = self.base_url.rstrip('/') + '/' + cover_url.lstrip('/')
            
            chapters = []
            chap_links = soup.select('#myUL a')
            for link in chap_links:
                href = link['href']
                parsed_href = urllib.parse.urlparse(href)
                chapters.append({
                    "id": parsed_href.path.strip('/'),
                    "title": link.text.strip(),
                    "date": ""
                })
            
            return {
                "id": manga_id,
                "title": title_tag.text.strip(),
                "cover": cover_url,
                "rating": 5.0,
                "author": "Đang cập nhật",
                "description": desc,
                "chapters": chapters
            }
        except Exception as e:
            print(f"[{self.name}] Details Error: {e}")
            return None

    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        url = f"{self.base_url}/{chapter_id}"
        html = None
        if HAS_CURL_CFFI:
            try:
                 async with AsyncSession(headers=self.headers, impersonate="chrome120", verify=False) as client:
                    resp = await client.get(url, timeout=20)
                    if resp.status_code == 200: html = resp.text
            except: pass
        
        if not html:
            html = await CurlWrapper.get(url)
            
        if not html: return {"id": chapter_id, "pages": []}

        try:
            soup = BeautifulSoup(html, 'html.parser')
            img_els = soup.select('#chapterContent img')
            
            pages = []
            for img in img_els:
                pg_url = img.get('data-src') or img.get('src')
                if pg_url:
                    if pg_url.startswith('//'): pg_url = 'https:' + pg_url
                    elif not pg_url.startswith('http'):
                        pg_url = self.base_url.rstrip('/') + '/' + pg_url.lstrip('/')
                    pages.append(pg_url)
            
            return {"id": chapter_id, "pages": pages}
        except Exception as e:
            print(f"[{self.name}] Pages Error: {e}")
            return {"id": chapter_id, "pages": []}

doctruyen5s = DocTruyen5SSource()
truyenvn = MadaraSource("TruyenVN", "https://truyenvn.shop")
from .foxtruyen import FoxTruyenSource
foxtruyen = FoxTruyenSource()
