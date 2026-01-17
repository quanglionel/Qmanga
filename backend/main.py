from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union
import uvicorn
import os
import httpx 
import otruyen 
import asyncio
from datetime import datetime

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/proxy")
async def proxy_image(url: str):
    if not url:
        return Response(status_code=404)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    # Add referer based on domain
    if "mangadex" in url:
        headers["Referer"] = "https://mangadex.org/"
    elif "comick" in url:
        headers["Referer"] = "https://comick.io/"
    elif "nettruyen" in url or "nettruyenco" in url:
        headers["Referer"] = "https://nettruyenar.com/"
    elif "truyenqq" in url or "truyenqqq" in url or "truyenqqno" in url:
        headers["Referer"] = "https://truyenqqno.com/"
    elif "blogtruyen" in url:
        headers["Referer"] = "https://blogtruyen.vn/"
    elif "cmanga" in url:
        headers["Referer"] = "https://cmanga.com/"
    elif "bato.to" in url or "batoto" in url:
        headers["Referer"] = "https://bato.to/"
    elif "sayhentai" in url:
        headers["Referer"] = "https://sayhentai.net/"
    elif "nhentai" in url:
        headers["Referer"] = "https://nhentai.net/"
    elif "hentaivn" in url:
        headers["Referer"] = "https://hentaivn.ooo/"
    elif "lxmanga" in url:
        headers["Referer"] = "https://lxmanga.net/"
    elif "cuutruyen" in url:
        headers["Referer"] = "https://cuutruyen.net/"
    elif "doctruyen3qi" in url:
        headers["Referer"] = "https://doctruyen3qi.com/"
    elif "truyentranh3q" in url:
        headers["Referer"] = "https://truyentranh3q.com/"
    elif "toptruyen" in url:
        headers["Referer"] = "https://toptruyen.net/"

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        try:
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                 return Response(status_code=resp.status_code)
            return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/jpeg"))
        except Exception as e:
            print(f"Proxy Error: {e} for {url}")
            return Response(status_code=404)

# --- Source Management ---
from otruyen import otruyen
from mangadex import mangadex 
from comick import comick
from cmanga import cmanga
from nettruyen import nettruyen
from truyenqq import truyenqq
from blogtruyen import blogtruyen

# Individual new sources
source_imports = [
    ("mangaplus", "MangaPlusSource"),
    ("manhwatop", "ManhwatopSource"),
    ("mangakakalot", "MangakakalotSource"),
    ("batoto", "BatotoSource"),
    ("sayhentai", "SayHentaiSource"),
    ("nhentai", "NHentaiSource"),
    ("hentaivn", "HentaiVNSource"),
    ("cuutruyen", "CuutruyenSource"),
    ("lxmanga", "LXMangaSource"),
    ("nhattruyen", "nhattruyen"),
]

NEW_SOURCES = {}

# Import from individual files
for module_name, class_name in source_imports:
    try:
        module = __import__(module_name)
        if hasattr(module, class_name):
            obj = getattr(module, class_name)
            NEW_SOURCES[module_name] = obj() if isinstance(obj, type) else obj
    except Exception as e:
        print(f"Failed to import {module_name}: {e}")

# Import aggregated clones
try:
    from aggregated_sources import (
        doctruyen3q, truyentranh3q, toptruyen, 
        nettruyenco, nettruyenx, vlogtruyen
    )
    NEW_SOURCES["doctruyen3q"] = doctruyen3q
    NEW_SOURCES["truyentranh3q"] = truyentranh3q
    NEW_SOURCES["toptruyen"] = toptruyen
    NEW_SOURCES["nettruyenco"] = nettruyenco
    NEW_SOURCES["nettruyenx"] = nettruyenx
    NEW_SOURCES["vlogtruyen"] = vlogtruyen
except Exception as e:
    print(f"Failed to load aggregated sources: {e}")


import json

# Simplified Source Registry
SOURCES = {
    "otruyen": otruyen,
    "mangadex": mangadex,
    "comick": comick,
    "cmanga": cmanga,
    "nettruyen": nettruyen,
    "truyenqq": truyenqq,
    "blogtruyen": blogtruyen,
}

# Add new sources
SOURCES.update(NEW_SOURCES)



ACTIVE_SOURCE_FILE = "active_source.json"

def load_active_source():
    if os.path.exists(ACTIVE_SOURCE_FILE):
        try:
            with open(ACTIVE_SOURCE_FILE, 'r') as f:
                data = json.load(f)
                sid = data.get('active_source')
                if sid in SOURCES:
                    return sid
        except:
            pass
    return "otruyen"

def save_active_source(sid):
    try:
        with open(ACTIVE_SOURCE_FILE, 'w') as f:
            json.dump({'active_source': sid}, f)
    except:
        pass

ACTIVE_SOURCE_ID = load_active_source()

def get_source():
    return SOURCES.get(ACTIVE_SOURCE_ID, otruyen)

@app.get("/api/sources")
@app.get("/api/extensions")
async def get_sources():
    """Return all available sources and which one is active"""
    results = []
    for sid, src in SOURCES.items():
        # Only include if actually implemented as a source class
        if hasattr(src, 'get_source_info'):
            info = src.get_source_info()
            info["id"] = sid
            info["active"] = (sid == ACTIVE_SOURCE_ID)
            results.append(info)
        else:
            # Fallback for sources not yet updated to BaseSource
            results.append({
                "id": sid,
                "name": sid.capitalize(),
                "active": (sid == ACTIVE_SOURCE_ID)
            })
    return results

@app.post("/api/sources/select/{source_id}")
async def select_source(source_id: str):
    global ACTIVE_SOURCE_ID
    if source_id in SOURCES:
        ACTIVE_SOURCE_ID = source_id
        save_active_source(source_id)
        return {"status": "success", "active_source": source_id}
    return {"status": "error", "message": "Source not found"}

# File-based persistence
LIBRARY_FILE = "user_library.json"
HISTORY_FILE = "reading_history.json"

# In-memory storage: { manga_id: { "current_chapter": {...}, "added_at": timestamp } }
USER_LIBRARY = {}
# Cache for library details to avoid re-fetching constantly
LIBRARY_CACHE = {}
# Reading history: list of { manga_id, title, cover, chapter_title, timestamp }
READING_HISTORY = []
MAX_HISTORY = 50 

# Notifications: list of { type, manga_id, title, chapter_title, timestamp, read }
NOTIFICATIONS = []
NOTIFICATION_FILE = "notifications.json"

# Chapter cache for offline reading: { chapter_id: { pages: [], cached_at: timestamp } }
CHAPTER_CACHE = {}
CHAPTER_CACHE_FILE = "chapter_cache.json"

def save_data():
    try:
        with open(LIBRARY_FILE, 'w', encoding='utf-8') as f:
            json.dump(USER_LIBRARY, f, ensure_ascii=False, indent=2)
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(READING_HISTORY, f, ensure_ascii=False, indent=2)
        with open(NOTIFICATION_FILE, 'w', encoding='utf-8') as f:
            json.dump(NOTIFICATIONS, f, ensure_ascii=False, indent=2)
        with open(CHAPTER_CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(CHAPTER_CACHE, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

def load_data():
    global USER_LIBRARY, READING_HISTORY
    if os.path.exists(LIBRARY_FILE):
        try:
            with open(LIBRARY_FILE, 'r', encoding='utf-8') as f:
                USER_LIBRARY = json.load(f)
        except: pass
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                READING_HISTORY = json.load(f)
        except: pass
    if os.path.exists(NOTIFICATION_FILE):
        try:
            with open(NOTIFICATION_FILE, 'r', encoding='utf-8') as f:
                NOTIFICATIONS = json.load(f)
        except: pass
    if os.path.exists(CHAPTER_CACHE_FILE):
        try:
            with open(CHAPTER_CACHE_FILE, 'r', encoding='utf-8') as f:
                CHAPTER_CACHE = json.load(f)
        except: pass

load_data()

def normalize_title(title: str) -> str:
    """Normalize title for duplicate detection (removes diacritics, special chars, and spaces)"""
    import re
    import unicodedata
    
    if not title:
        return ""
        
    # Lowercase
    text = title.lower()
    
    # Normalize unicode (NFD decomposes characters into base + diacritic)
    text = unicodedata.normalize('NFD', text)
    # Filter out diacritics (Non-spacing Mark category)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    # Manual fixes for D/d
    text = text.replace('đ', 'd').replace('Đ', 'D')
    
    # Remove special chars and spaces
    normalized = re.sub(r'[^\w\s]', '', text)
    normalized = re.sub(r'\s+', '', normalized)
    return normalized


@app.get("/api/trending")
async def get_trending(page: int = 1, sources: str = None, lang: str = None):
    """Fetch trending from selected sources and merge results with smart deduplication"""
    try:
        # Define sources language mapping (internal)
        SOURCE_LANGS = {
            "otruyen": "vi",
            "cmanga": "vi",
            "nettruyen": "vi",
            "truyenqq": "vi",
            "blogtruyen": "vi",
            "manhwatop": "vi",
            "sayhentai": "vi",
            "hentaivn": "vi",
            "cuutruyen": "vi",
            "lxmanga": "vi",
            "nhattruyen": "vi",
            "doctruyen3q": "vi",
            "truyentranh3q": "vi",
            "toptruyen": "vi",
            "nettruyenco": "vi",
            "nettruyenx": "vi",
            "vlogtruyen": "vi",
            "mangadex": "multi",
            "comick": "multi",
            "batoto": "multi",
            "nhentai": "multi",
            "mangaplus": "multi",
            "mangakakalot": "en"
        }

        # Parse source filter
        if sources:
            selected_sources = [s.strip() for s in sources.split(',') if s.strip() in SOURCES]
        else:
            selected_sources = list(SOURCES.keys())
        
        # Apply language filtering if requested
        if lang == 'vi':
            # Strictly use only Vietnamese-first sources
            selected_sources = [s for s in selected_sources if SOURCE_LANGS.get(s) == 'vi']
            print(f"[API] Chỉ giữ lời nguồn tiếng Việt: {selected_sources}")
        
        print(f"[API] Đang lấy trending từ {len(selected_sources)} nguồn, trang: {page}")

        
        # Fetch from selected sources in parallel
        async def fetch_from_source(source_id, source):
            try:
                if hasattr(source, 'fetch_trending'):
                    res = await source.fetch_trending(page=page, limit=50)
                else:
                    res = await source.fetch_trending_manga(page=page)
                
                items = res.get('active_manga', []) if isinstance(res, dict) else []
                is_nsfw_source = getattr(source, 'is_nsfw', False)
                # Add source info to each item
                for item in items:
                    item['source'] = source_id
                    item['source_name'] = source.name if hasattr(source, 'name') else source_id
                    item['is_nsfw'] = is_nsfw_source
                return items
            except Exception as e:
                print(f"[API] Lỗi từ {source_id}: {e}")
                return []
        
        # Create tasks for selected sources only
        tasks = []
        for source_id in selected_sources:
            if source_id in SOURCES:
                tasks.append(fetch_from_source(source_id, SOURCES[source_id]))
        
        # Wait for all sources
        all_results = await asyncio.gather(*tasks)

        
        # Smart deduplication: keep manga with latest chapter / most recent update
        title_to_manga = {}  # normalized_title -> best manga item
        
        def extract_chapter_number(chapter_str):
            """Extract chapter number from string like 'Chapter 123' or 'Chap 123.5'"""
            if not chapter_str:
                return 0
            import re
            match = re.search(r'(\d+(?:\.\d+)?)', str(chapter_str))
            return float(match.group(1)) if match else 0
        
        def parse_update_time(time_str):
            """Convert update time to sortable value (higher = more recent)"""
            if not time_str:
                return 0
            time_str = str(time_str).lower()
            
            # Handle relative times
            if 'giây' in time_str or 'second' in time_str:
                return 1000000
            if 'phút' in time_str or 'minute' in time_str:
                return 100000
            if 'giờ' in time_str or 'hour' in time_str:
                return 10000
            if 'ngày' in time_str or 'day' in time_str:
                return 1000
            if 'tuần' in time_str or 'week' in time_str:
                return 100
            if 'tháng' in time_str or 'month' in time_str:
                return 10
            if 'năm' in time_str or 'year' in time_str:
                return 1
            return 0
        
        for source_items in all_results:
            for item in source_items:
                normalized = normalize_title(item.get('title', ''))
                if not normalized:
                    continue
                
                current_chapter = extract_chapter_number(item.get('latest_chapter', ''))
                current_update = parse_update_time(item.get('update_time', ''))
                
                if normalized in title_to_manga:
                    existing = title_to_manga[normalized]
                    existing_chapter = extract_chapter_number(existing.get('latest_chapter', ''))
                    existing_update = parse_update_time(existing.get('update_time', ''))
                    
                    # Keep the one with higher chapter number, or if equal, more recent update
                    if current_chapter > existing_chapter:
                        title_to_manga[normalized] = item
                    elif current_chapter == existing_chapter and current_update > existing_update:
                        title_to_manga[normalized] = item
                else:
                    title_to_manga[normalized] = item
        
        # Convert back to list and limit
        merged = list(title_to_manga.values())[:100]
        
        print(f"[API] Tổng cộng: {len(merged)} truyện (đã loại trùng thông minh)")
        
        return {
            "active_manga": merged,
            "new_manga": []
        }
        
    except Exception as e:
        print(f"Error fetching trending: {e}")
        return {"active_manga": [], "new_manga": []}

@app.get("/api/search")
async def search_manga(q: str, source: str = None):
    """Search for manga by title in a specific source"""
    try:
        if not q or len(q) < 2:
            return {"results": []}
        
        # Use specified source or all sources
        sources_to_search = {}
        if source and source in SOURCES:
            sources_to_search[source] = SOURCES[source]
        else:
            sources_to_search = SOURCES
        
        # Normalize search query
        query_normalized = normalize_title(q)
        query_words = query_normalized.split()
        
        results = []
        
        for src_id, src in sources_to_search.items():
            try:
                # Get items to search through - try multiple pages for better coverage
                all_items = []
                for page in range(1, 4):  # Search first 3 pages
                    try:
                        if hasattr(src, 'fetch_trending'):
                            data = await src.fetch_trending(page=page, limit=50)
                        else:
                            data = await src.fetch_trending_manga(page=page)
                        
                        items = data.get('active_manga', []) if isinstance(data, dict) else []
                        all_items.extend(items)
                    except:
                        break
                
                for item in all_items:
                    title = item.get('title', '')
                    title_normalized = normalize_title(title)
                    
                    # Check if query matches title (fuzzy match)
                    match_score = 0
                    for word in query_words:
                        if word in title_normalized:
                            match_score += 1
                    
                    # At least half the words should match
                    if match_score >= len(query_words) / 2:
                        item['source'] = src_id
                        item['match_score'] = match_score
                        results.append(item)
                        
            except Exception as e:
                print(f"Search error in {src_id}: {e}")
        
        # Sort by match score (higher is better)
        results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
        
        # Remove duplicates by title
        seen_titles = set()
        unique_results = []
        for r in results:
            title_key = normalize_title(r.get('title', ''))
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_results.append(r)
        
        return {"results": unique_results[:20]}
        
    except Exception as e:
        print(f"Search error: {e}")
        return {"results": []}




@app.get("/api/manga/{manga_id}")

async def get_manga_details(manga_id: str, source: str = None):
    try:
        # Use specified source or fall back to active source
        if source and source in SOURCES:
            src = SOURCES[source]
        else:
            src = get_source()
            
        if hasattr(src, 'fetch_manga_details'):
            data = await src.fetch_manga_details(manga_id)
        else:
            data = await src.fetch_manga_details(manga_id)
            
        if data:
            # Add source info to data
            data['source'] = source if source else ACTIVE_SOURCE_ID
            if manga_id in USER_LIBRARY:
                LIBRARY_CACHE[manga_id] = data
            return data
        return {"error": "Manga not found"}
    except Exception as e:
        print(f"Error fetching details: {e}")
        return {"error": str(e)}


@app.get("/api/chapter/{chapter_id:path}") # Using path type to allow URLs as ID
async def get_chapter_pages(chapter_id: str):
    # Check cache first for offline reading
    if chapter_id in CHAPTER_CACHE:
        cached = CHAPTER_CACHE[chapter_id]
        print(f"[Cache] Đọc từ cache: {cached.get('chapter_title', chapter_id)}")
        return {"id": chapter_id, "pages": cached['pages'], "cached": True}
    
    try:
        source = get_source()
        if hasattr(source, 'fetch_chapter_pages'):
            result = await source.fetch_chapter_pages(chapter_id)
        else:
            result = await source.fetch_chapter_pages(chapter_id)
        
        # Cache the result for future offline access
        if result and result.get('pages'):
            CHAPTER_CACHE[chapter_id] = {
                "pages": result['pages'],
                "cached_at": datetime.now().isoformat()
            }
            save_data()
        
        return result
    except Exception as e:
        print(f"Error fetching chapter: {e}")
        return {"error": str(e)}


class ProgressUpdate(BaseModel):
    chapter_id: str
    chapter_title: str

class HistoryEntry(BaseModel):
    manga_id: str
    manga_title: str
    manga_cover: str
    chapter_title: str

@app.post("/api/progress/{manga_id}")
async def update_progress(manga_id: str, progress: ProgressUpdate):
    import time
    
    # Update library progress if in library
    if manga_id in USER_LIBRARY:
        USER_LIBRARY[manga_id]['current_chapter'] = {
            "id": progress.chapter_id,
            "title": progress.chapter_title
        }
    
    # Add to reading history
    # Get manga details from cache or fetch
    details = LIBRARY_CACHE.get(manga_id)
    if not details:
        try:
            details = await otruyen.fetch_manga_details(manga_id)
        except:
            details = None
    
    if details:
        # Remove old entry for same manga if exists
        global READING_HISTORY
        READING_HISTORY = [h for h in READING_HISTORY if h.get('manga_id') != manga_id]
        
        # Add new entry at the beginning
        READING_HISTORY.insert(0, {
            "manga_id": manga_id,
            "manga_title": details.get('title', 'Unknown'),
            "manga_cover": details.get('cover', ''),
            "chapter_title": progress.chapter_title,
            "timestamp": time.time()
        })
        
        # Trim to max history
        READING_HISTORY = READING_HISTORY[:MAX_HISTORY]
        save_data()
    
    return {"status": "ok"}

@app.get("/api/history")
async def get_history():
    # Return history entries formatted for frontend
    return [{
        "id": h["manga_id"],
        "title": h["manga_title"],
        "cover": h["manga_cover"],
        "latest_chapter": h["chapter_title"],  # Show last read chapter
        "updated_at": ""
    } for h in READING_HISTORY]

@app.get("/api/library")
async def get_library():
    results = []
    source = get_source()
    for mid, user_data in USER_LIBRARY.items():
        details = LIBRARY_CACHE.get(mid)
        if not details:
            try:
                if hasattr(source, 'fetch_manga_details'):
                    details = await source.fetch_manga_details(mid)
                else:
                    details = await source.fetch_manga_details(mid)
                if details:
                    LIBRARY_CACHE[mid] = details
            except:
                continue
        
        if details:
            latest_chap = details['chapters'][0]['title'] if details['chapters'] else "N/A"
            current_chap = user_data.get('current_chapter', {}).get('title', 'Not Started')
            added_at = user_data.get('added_at', 0)
            
            results.append({
                "id": details['id'],
                "title": details['title'],
                "cover": details['cover'],
                "latest_chapter_string": latest_chap,
                "current_chapter_string": current_chap,
                "added_at": added_at
            })
    
    # Sort by added_at descending
    results.sort(key=lambda x: x['added_at'], reverse=True)
    return results

@app.post("/api/library/{manga_id}")
async def add_to_library(manga_id: str):
    import time
    if manga_id not in USER_LIBRARY:
        USER_LIBRARY[manga_id] = {"added_at": time.time()}
        
    # Get details to store the current latest chapter (so we don't notify immediately)
    try:
        source = get_source()
        if hasattr(source, 'fetch_manga_details'):
            details = await source.fetch_manga_details(manga_id)
        else:
            details = await source.fetch_manga_details(manga_id)
        
        if details:
            LIBRARY_CACHE[manga_id] = details
            if details.get('chapters'):
                USER_LIBRARY[manga_id]['last_seen_chapter_id'] = details['chapters'][0]['id']
    except:
        pass
        
    save_data()
    return {"status": "added", "manga_id": manga_id}

@app.delete("/api/library/{manga_id}")
async def remove_from_library(manga_id: str):
    if manga_id in USER_LIBRARY:
        del USER_LIBRARY[manga_id]
        if manga_id in LIBRARY_CACHE:
            del LIBRARY_CACHE[manga_id]
        save_data()
        return {"status": "removed", "manga_id": manga_id}
    return {"error": "Manga not in library"}

@app.get("/api/extensions")
async def get_extensions_compat():
    """Compatibility endpoint for frontend using /api/extensions"""
    return await get_sources()

# Mount the frontend static files
# Note: In a real deployment, you might serve specific routes or use a separate frontend server.
# For this simple fullstack setup, we'll serve the static directory.
ABS_FRONTEND_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
app.mount("/", StaticFiles(directory=ABS_FRONTEND_PATH, html=True), name="static")

# --- Background Task: Check for Updates ---
async def check_for_updates():
    """Periodically check all manga in library for new chapters"""
    global NOTIFICATIONS
    print("[Background] Bắt đầu tác vụ kiểm tra chương mới...")
    while True:
        try:
            # Check every 30 minutes
            await asyncio.sleep(1800) 
            
            if not USER_LIBRARY:
                continue
                
            print(f"[Background] Đang kiểm tra {len(USER_LIBRARY)} truyện trong thư viện...")
            source = get_source()
            
            for mid, user_data in USER_LIBRARY.items():
                try:
                    # Fetch details to get latest chapter
                    details = await source.fetch_manga_details(mid)
                    if not details or not details.get('chapters'):
                        continue
                        
                    current_latest = details['chapters'][0]
                    last_seen_id = user_data.get('last_seen_chapter_id')
                    
                    if last_seen_id and current_latest['id'] != last_seen_id:
                        # New chapter found!
                        print(f"[Update] Chương mới cho {details['title']}: {current_latest['title']}")
                        
                        # Auto-preload the new chapter
                        try:
                            chapter_data = await source.fetch_chapter_pages(current_latest['id'])
                            if chapter_data and chapter_data.get('pages'):
                                CHAPTER_CACHE[current_latest['id']] = {
                                    "pages": chapter_data['pages'],
                                    "manga_id": mid,
                                    "manga_title": details['title'],
                                    "chapter_title": current_latest['title'],
                                    "cached_at": datetime.now().isoformat()
                                }
                                print(f"[Cache] Đã tải trước {len(chapter_data['pages'])} trang cho {current_latest['title']}")
                        except Exception as cache_err:
                            print(f"[Cache] Lỗi tải trước: {cache_err}")
                        
                        # Add notification
                        # Check if notification already exists for this chapter
                        dup = any(n['manga_id'] == mid and n['chapter_id'] == current_latest['id'] for n in NOTIFICATIONS)
                        if not dup:
                            NOTIFICATIONS.insert(0, {
                                "type": "new_chapter",
                                "manga_id": mid,
                                "manga_title": details['title'],
                                "chapter_id": current_latest['id'],
                                "chapter_title": current_latest['title'],
                                "timestamp": datetime.now().isoformat(),
                                "read": False,
                                "cached": current_latest['id'] in CHAPTER_CACHE
                            })
                            # Trim to last 20 notifications
                            while len(NOTIFICATIONS) > 20: 
                                NOTIFICATIONS.pop()
                            save_data()
                            
                        # Update last seen chapter
                        USER_LIBRARY[mid]['last_seen_chapter_id'] = current_latest['id']
                        save_data()
                except Exception as e:
                    print(f"Error checking {mid}: {e}")
                    
        except Exception as e:
            print(f"Background worker error: {e}")
            await asyncio.sleep(60)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(check_for_updates())

@app.get("/api/notifications")
async def get_notifications():
    return NOTIFICATIONS

@app.post("/api/notifications/read-all")
async def read_all_notifications():
    for n in NOTIFICATIONS:
        n['read'] = True
    save_data()
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
