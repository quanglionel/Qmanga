
from .nettruyen import NetTruyenSource
from bs4 import BeautifulSoup
import re
import httpx

class FoxTruyenSource(NetTruyenSource):
    def __init__(self):
        super().__init__()
        self.priority = 5
        self.id = "foxtruyen"
        self.name = "FoxTruyen"
        self.base_url = "https://foxtruyen2.com"
        self.headers.update({'Referer': f'{self.base_url}/'})

    async def get_html(self, url):
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=10.0, follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    return response.text
                print(f"[FoxTruyen] Failed to fetch {url}, status: {response.status_code}")
                return None
        except Exception as e:
            print(f"[FoxTruyen] Error fetching {url}: {e}")
            return None

    async def fetch_trending(self, page=1, limit=20):
        url = f"{self.base_url}/truyen-moi-cap-nhat/trang-{page}.html"
        data = await self.get_html(url)
        if not data:
            return {'active_manga': [], 'new_manga': []}

        soup = BeautifulSoup(data, 'html.parser')
        manga_list = []

        # Selector updated for FoxTruyen2 structure
        items = soup.select('.list_item_home .item_home')

        for item in items:
            try:
                title_tag = item.select_one('.book_name')
                if not title_tag:
                    continue
                
                title = title_tag.text.strip()
                link = title_tag.get('href')
                
                # Extract ID from link (e.g., .../slug-1234.html -> slug-1234)
                # FoxTruyen ID logic: keep the full relative part or slug
                # Let's keep the slug part after truyen-tranh/
                if '/truyen-tranh/' in link:
                    manga_id = link.split('/truyen-tranh/')[-1].replace('.html', '')
                else:
                    manga_id = link.split('/')[-1].replace('.html', '')

                cover_img = item.select_one('img.lazy-image')
                cover = ""
                if cover_img:
                    cover = cover_img.get('data-src') or cover_img.get('src')
                
                # Helper to fix relative URLs
                if cover and not cover.startswith('http'):
                     cover = f"{self.base_url}{cover}"

                # Latest chapter
                chap_tag = item.select_one('a.cl99')
                latest_chapter = "N/A"
                if chap_tag:
                    latest_chapter = chap_tag.text.strip()

                manga_list.append({
                    'id': manga_id,
                    'title': title,
                    'cover': cover,
                    'latest_chapter': latest_chapter,
                    'source': self.id,
                    'source_name': self.name,
                    'url': link  # Keep full URL for reference
                })
            except Exception as e:
                print(f"[FoxTruyen] Error parsing item: {e}")
                continue

        return {'active_manga': manga_list, 'new_manga': []}

    async def fetch_manga_details(self, manga_id):
        # FoxTruyen details logic
        # URL pattern: base_url/truyen-tranh/{manga_id}.html
        url = f"{self.base_url}/truyen-tranh/{manga_id}.html"
        data = await self.get_html(url)
        if not data:
            return None

        soup = BeautifulSoup(data, 'html.parser')
        
        # Info block
        title_tag = soup.select_one('.title_tale h1')
        title = title_tag.text.strip() if title_tag else "Unknown"
        
        cover_img = soup.select_one('.thumbblock img')
        cover = cover_img.get('src') if cover_img else ""
        if cover and not cover.startswith('http'):
            cover = f"{self.base_url}{cover}"
        
        desc_div = soup.select_one('.story-detail-info')
        description = desc_div.text.strip() if desc_div else ""
        
        author_tag = soup.select_one('.info_tale .org')
        author = author_tag.text.strip() if author_tag else "Updating..."

        # Chapters
        chapters = []
        # Correct selector based on dump: .list_chap .item_chap a
        chap_links = soup.select('.list_chap .item_chap .wc110 a')

        for link in chap_links:
            chap_title = link.text.strip()
            chap_url = link.get('href')
            # ID from URL
            if not chap_url: continue
            
            # extract id: .../hoang-de-minami-54760-chap-22.html -> hoang-de-minami-54760-chap-22
            chap_id = chap_url.split('/')[-1].replace('.html', '')
            
            chapters.append({
                'id': chap_id,
                'title': chap_title,
                'url': chap_url
            })
            
        return {
            'id': manga_id,
            'title': title,
            'cover': cover,
            'author': author,
            'description': description,
            'chapters': chapters
        }

    async def fetch_chapter_pages(self, chapter_id):
        # Construct URL. ID is the full slug here.
        url = f"{self.base_url}/truyen-tranh/{chapter_id}.html"
        data = await self.get_html(url)
        if not data:
            return {'id': chapter_id, 'pages': []}
            
        soup = BeautifulSoup(data, 'html.parser')
        # FoxTruyen specific: .content_detail_manga img
        img_tags = soup.select('.content_detail_manga img, .read-content img, .box_doc img')
        
        images = []
        for img in img_tags:
            src = img.get('src') or img.get('data-src') or img.get('data-original')
            if src:
                if not src.startswith('http'):
                    # Check if relative or protocol-relative
                    if src.startswith('//'):
                        src = f"https:{src}"
                    else:
                        src = f"{self.base_url}{src}"
                
                # Filter out obvious logo/icons if needed, though specific selector helps
                if 'logo' in src.lower() or 'icon' in src.lower():
                    continue
                    
                images.append(src)
                
        return {'id': chapter_id, 'pages': images}
