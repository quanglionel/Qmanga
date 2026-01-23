"""
MangaDex Source - Implementation of BaseSource for api.mangadex.org
"""

import httpx
from typing import List, Dict, Optional
from .base import BaseSource


class MangaDexSource(BaseSource):
    """Manga source implementation for MangaDex API"""
    
    name = "MangaDex"
    language = "Multi"
    base_url = "https://api.mangadex.org"
    icon = "https://mangadex.org/favicon.ico"
    
    cache_file = "mangadex_cache.json"
    
    async def fetch_trending(self, page: int = 1, limit: int = 100) -> List[Dict]:
        """Fetch popular manga from MangaDex"""
        cache_key = f"trending_{page}_{limit}"
        
        cached = self.get_from_cache(cache_key)
        if cached:
            return cached
            
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Calculate offset
                offset = (page - 1) * limit
                
                params = {
                    "limit": limit,
                    "offset": offset,
                    "order[followedCount]": "desc",
                    "includes[]": ["cover_art"]
                }
                
                resp = await client.get(f"{self.base_url}/manga", params=params)
                if resp.status_code != 200:
                    return {"active_manga": [], "new_manga": []}
                    
                data = resp.json()
                
                results = []
                for manga in data.get('data', []):
                    manga_id = manga['id']
                    attrs = manga['attributes']
                    
                    # Find cover
                    cover_file = ""
                    for rel in manga.get('relationships', []):
                        if rel['type'] == 'cover_art' and 'attributes' in rel:
                            cover_file = rel['attributes'].get('fileName', '')
                            break
                    
                    cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_file}.256.jpg" if cover_file else "https://via.placeholder.com/200x300"
                    
                    # Priority title: VI -> EN -> others
                    title = attrs['title'].get('vi') or attrs['title'].get('en') or list(attrs['title'].values())[0]
                    
                    results.append({
                        "id": manga_id,
                        "title": title,
                        "cover": cover_url,
                        "latest_chapter": "N/A", # MangaDex requires feed fetch per manga for this, keep simple for now
                        "updated_at": attrs.get('updatedAt', '')
                    })
                
                # MangaDex results are categorized as active by default since we follow popular ones
                response = {
                    "active_manga": results,
                    "new_manga": []
                }
                
                self.set_cache(cache_key, response)
                return response
                
            except Exception as e:
                print(f"[MangaDex] Trending Error: {e}")
                return {"active_manga": [], "new_manga": []}
    
    async def fetch_manga_details(self, manga_id: str) -> Optional[Dict]:
        """Fetch detailed info from MangaDex"""
        async with httpx.AsyncClient() as client:
            try:
                params = {"includes[]": ["cover_art", "author"]}
                resp = await client.get(f"{self.base_url}/manga/{manga_id}", params=params)
                data = resp.json()
                
                if 'data' not in data:
                    return None
                    
                manga = data['data']
                attrs = manga['attributes']
                
                cover_file = ""
                author_name = "Unknown"
                for rel in manga.get('relationships', []):
                    if rel['type'] == 'cover_art' and 'attributes' in rel:
                        cover_file = rel['attributes'].get('fileName', '')
                    if rel['type'] == 'author' and 'attributes' in rel:
                        author_name = rel['attributes'].get('name', 'Unknown')
                
                cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_file}" if cover_file else ""
                
                title = attrs['title'].get('vi') or attrs['title'].get('en') or list(attrs['title'].values())[0]
                desc = attrs['description'].get('vi') or attrs['description'].get('en', 'No description')
                
                # Chapters - Fetch Vietnamese first, fallback to English
                feed_params = {
                    "limit": 100,
                    "translatedLanguage[]": ["vi", "en"],
                    "order[chapter]": "desc",
                    "includeFutureUpdates": "0"
                }
                feed_resp = await client.get(f"{self.base_url}/manga/{manga_id}/feed", params=feed_params)
                feed_data = feed_resp.json()
                
                chapters = []
                for chap in feed_data.get('data', []):
                    attr = chap['attributes']
                    if attr.get('externalUrl') or attr.get('pages', 0) == 0:
                        continue

                    lang = attr['translatedLanguage']
                    title_prefix = f"[{lang.upper()}] " if lang != 'vi' else ""
                    
                    chapters.append({
                        "id": chap['id'],
                        "title": f"{title_prefix}Ch. {attr.get('chapter', '?')} - {attr.get('title', '') or ''}",
                        "date": attr['publishAt'][:10]
                    })
                
                return {
                    "id": manga_id,
                    "title": title,
                    "cover": cover_url,
                    "rating": 5.0,
                    "author": author_name,
                    "description": desc,
                    "chapters": chapters
                }
            except Exception as e:
                print(f"[MangaDex] Details Error: {e}")
                return None
    
    async def fetch_chapter_pages(self, chapter_id: str) -> Dict:
        """Fetch pages for a chapter from MangaDex"""
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.get(f"{self.base_url}/at-home/server/{chapter_id}")
                data = resp.json()
                
                base_url = data['baseUrl']
                chapter_hash = data['chapter']['hash']
                filenames = data['chapter']['data']
                
                pages = [f"{base_url}/data/{chapter_hash}/{fname}" for fname in filenames]
                
                return {
                    "id": chapter_id,
                    "pages": pages
                }
            except Exception as e:
                print(f"[MangaDex] Pages Error: {e}")
                return {"id": chapter_id, "pages": []}


# Singleton instance
mangadex = MangaDexSource()


