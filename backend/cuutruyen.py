"""
CuuTruyen Source - Implementation of BaseSource for cuutruyen.net
"""

import httpx
from typing import List, Dict, Optional
from base_source import BaseSource

class CuutruyenSource(BaseSource):
    """Manga source implementation for CuuTruyen API"""
    
    name = "Cứu Truyện"
    language = "VI"
    base_url = "https://cuutruyen.net/api/v2"
    icon = "https://cuutruyen.net/favicon.ico"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://cuutruyen.net/"
    }
    
    async def fetch_trending(self, page: int = 1, limit: int = 40) -> Dict:
        """Fetch popular manga from CuuTruyen"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                # Cuutruyen API for trending
                # Using /comics/trending or /comics (latest)
                url = f"{self.base_url}/comics?page={page}&limit={limit}&order_by=updated_at"
                resp = await client.get(url)
                data = resp.json()
                
                results = []
                for manga in data.get('data', []):
                    # Map to common structure
                    manga_id = manga.get('id')
                    results.append({
                        "id": str(manga_id),
                        "title": manga.get('title'),
                        "cover": manga.get('cover_url'),
                        "latest_chapter": f"Ch. {manga.get('latest_chapter_number', 'N/A')}",
                        "update_time": manga.get('updated_at', '')
                    })
                
                return {
                    "active_manga": results,
                    "new_manga": []
                }
            except Exception as e:
                print(f"[CuuTruyen] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}

    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch manga details from CuuTruyen"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                url = f"{self.base_url}/comics/{manga_id}"
                resp = await client.get(url)
                data = resp.json().get('data', {})
                
                # Chapters
                chapters_url = f"{self.base_url}/comics/{manga_id}/chapters"
                chap_resp = await client.get(chapters_url)
                chap_data = chap_resp.json().get('data', [])
                
                chapters = []
                for chap in chap_data:
                    chapters.append({
                        "id": str(chap.get('id')),
                        "title": f"Chương {chap.get('number')} - {chap.get('name') or ''}",
                        "date": chap.get('created_at', '')[:10]
                    })
                
                return {
                    "id": str(manga_id),
                    "title": data.get('title'),
                    "cover": data.get('cover_url'),
                    "author": data.get('author_name', 'Unknown'),
                    "description": data.get('description', 'Chưa có mô tả.'),
                    "chapters": chapters,
                    "source": "cuutruyen"
                }
            except Exception as e:
                print(f"[CuuTruyen] Details Error: {e}")
                return None

    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from CuuTruyen"""
        async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
            try:
                url = f"{self.base_url}/chapters/{chapter_id}"
                resp = await client.get(url)
                data = resp.json().get('data', {})
                
                pages = []
                for page in data.get('pages', []):
                    pages.append(page.get('url'))
                
                return {
                    "id": str(chapter_id),
                    "pages": pages
                }
            except Exception as e:
                print(f"[CuuTruyen] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}
