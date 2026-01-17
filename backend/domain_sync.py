import httpx
import json
import os
import asyncio

KEI_INDEX_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.json"
DOMAINS_CACHE_FILE = "dynamic_domains.json"

# Mapping between Keiyoushi package IDs/names and our internal source IDs
# This helps us identify which URL belongs to which source in our app
SOURCE_MAPPING = {
    # Keiyoushi Name/Pkg : Our ID
    "nettruyen": "nettruyen",
    "truyenqq": "truyenqq",
    "blogtruyen": "blogtruyen",
    "cmanga": "cmanga",
    "otruyen": "otruyen",
    "hentaivn": "hentaivn",
    "sayhentai": "sayhentai",
    "lxmanga": "lxmanga",
    "cuutruyen": "cuutruyen",
    "nhattruyen": "nhattruyen",
    "doctruyen3q": "doctruyen3q",
    "truyentranh3q": "truyentranh3q",
    "toptruyen": "toptruyen",
    "vlogtruyen": "vlogtruyen",
    "mangadex": "mangadex",
    "comick": "comick",
    "mangaplus": "mangaplus",
    "batoto": "batoto",
    "nhentai": "nhentai",
    "mangakakalot": "mangakakalot",
    "manhwatop": "manhwatop"
}

async def sync_domains():
    print("[Sync] Khởi động đồng bộ hóa tên miền từ Keiyoushi...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(KEI_INDEX_URL)
            if resp.status_code != 200:
                print(f"[Sync] Lỗi: Không thể tải index.json (Status: {resp.status_code})")
                return None
            
            extensions = resp.json()
            updated_domains = {}
            
            for ext in extensions:
                name_lower = ext.get('name', '').lower()
                pkg = ext.get('pkg', '').lower()
                
                # Check if this extension matches any of our sources
                found_id = None
                for key, source_id in SOURCE_MAPPING.items():
                    if key in name_lower or key in pkg:
                        found_id = source_id
                        break
                
                if found_id:
                    # Extracts the baseUrl from the sources list
                    sources = ext.get('sources', [])
                    if sources:
                        # Sometimes there are multiple sources in one extension (like multi-language)
                        # We pick the first one or try to match the language if it's a specific one
                        base_url = sources[0].get('baseUrl')
                        if base_url:
                            updated_domains[found_id] = base_url

            # Save to local cache
            with open(DOMAINS_CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(updated_domains, f, ensure_ascii=False, indent=2)
            
            print(f"[Sync] Thành công! Đã cập nhật {len(updated_domains)} tên miền.")
            return updated_domains
            
        except Exception as e:
            print(f"[Sync] Lỗi nghiêm trọng: {e}")
            return None

def get_cached_domains():
    if os.path.exists(DOMAINS_CACHE_FILE):
        try:
            with open(DOMAINS_CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

if __name__ == "__main__":
    asyncio.run(sync_domains())
