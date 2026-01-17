"""
MangaPlus Source - Implementation for MangaPlus by Shueisha (Official)
Free official manga from Shueisha (One Piece, Naruto, etc.)
"""

import httpx
from typing import List, Dict
from base_source import BaseSource


class MangaPlusSource(BaseSource):
    """Manga source implementation for MangaPlus"""
    
    name = "MangaPlus"
    language = "EN"
    base_url = "https://jumpg-webapi.tokyo-cdn.com/api"
    icon = "https://mangaplus.shueisha.co.jp/favicon.ico"
    
    cache_file = "mangaplus_cache.json"
    CACHE_TTL = 3600
    
    async def fetch_trending(self, page: int = 1, limit: int = 50) -> List[Dict]:
        """Fetch popular manga from MangaPlus"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # MangaPlus API for ranking
                resp = await client.get(
                    f"{self.base_url}/title_list/ranking",
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://mangaplus.shueisha.co.jp/"
                    }
                )
                
                if resp.status_code != 200:
                    return {"active_manga": [], "new_manga": []}
                
                # MangaPlus uses protobuf, this is a simplified approach
                # In reality, you'd need to parse protobuf response
                data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                
                results = []
                titles = data.get('success', {}).get('titleRankingView', {}).get('titles', [])
                
                for item in titles[:limit]:
                    manga_id = str(item.get('titleId', ''))
                    title = item.get('name', 'Unknown')
                    author = item.get('author', '')
                    cover = f"https://meo.comick.pictures/{item.get('portraitImageUrl', '')}"
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": cover,
                        "author": author,
                        "latest_chapter": "",
                        "rating": None,
                        "update_time": ""
                    })
                
                result = {"active_manga": results, "new_manga": []}
                self.save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                print(f"MangaPlus trending error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Dict:
        """Fetch manga details from MangaPlus"""
        cache_key = f"details_{manga_id}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/title_detail",
                    params={"title_id": manga_id},
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://mangaplus.shueisha.co.jp/"
                    }
                )
                
                if resp.status_code != 200:
                    return None
                
                data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                
                title_detail = data.get('success', {}).get('titleDetailView', {})
                title = title_detail.get('title', {})
                
                chapters = []
                for group in title_detail.get('chapterListGroup', []):
                    for ch in group.get('firstChapterList', []) + group.get('lastChapterList', []):
                        chapters.append({
                            "id": str(ch.get('chapterId', '')),
                            "title": ch.get('name', '') or f"Chapter {ch.get('chapterNumber', '')}",
                            "date": ""
                        })
                
                result = {
                    "id": manga_id,
                    "title": title.get('name', 'Unknown'),
                    "cover": f"https://meo.comick.pictures/{title.get('portraitImageUrl', '')}",
                    "author": title.get('author', ''),
                    "description": title_detail.get('overview', ''),
                    "chapters": chapters,
                    "rating": None
                }
                
                self.save_to_cache(cache_key, result)
                return result
                
            except Exception as e:
                print(f"MangaPlus details error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> List[str]:
        """Fetch chapter pages from MangaPlus"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/manga_viewer",
                    params={"chapter_id": chapter_id, "split": "yes", "img_quality": "super_high"},
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://mangaplus.shueisha.co.jp/"
                    }
                )
                
                if resp.status_code != 200:
                    return []
                
                data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                
                pages = []
                for page in data.get('success', {}).get('mangaViewer', {}).get('pages', []):
                    if page.get('mangaPage'):
                        img_url = page['mangaPage'].get('imageUrl', '')
                        if img_url:
                            pages.append(img_url)
                
                return pages
                
            except Exception as e:
                print(f"MangaPlus pages error: {e}")
                return []
