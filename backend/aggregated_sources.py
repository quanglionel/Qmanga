"""
Aggregated sources that use common structures (NetTruyen, TruyenQQ, etc.)
"""

from nettruyen import NetTruyenSource

class GenericNettruyenSource(NetTruyenSource):
    """A helper to quickly add NetTruyen clones"""
    def __init__(self, name, base_url, icon=None):
        super().__init__()
        self.name = name
        self.base_url = base_url
        self.icon = icon or f"{base_url}/favicon.ico"
        self.cache_file = f"{name.lower().replace(' ', '_')}_cache.json"
        self.headers["Referer"] = f"{base_url}/"

# SFW Sources
doctruyen3q = GenericNettruyenSource("DocTruyen3Q", "https://doctruyen3qi.com")
truyentranh3q = GenericNettruyenSource("TruyenTranh3Q", "https://truyentranh3q.com")
toptruyen = GenericNettruyenSource("TopTruyen", "https://toptruyen.net")
nettruyenco = GenericNettruyenSource("NetTruyenCO", "https://nettruyenco.vn")
nettruyenx = GenericNettruyenSource("NetTruyenX", "https://nettruyenx.com")
vlogtruyen = GenericNettruyenSource("VlogTruyen", "https://vlogtruyen2.net")

# NSFW/Specific Sources
# Tranh18, MeHentai, XXManhwa often share structures
class MadaraSource(NetTruyenSource):
    """Base for sources using Madara theme (WP) - slightly different but often works with BeautifulSoup"""
    def __init__(self, name, base_url, is_nsfw=False):
        super().__init__()
        self.name = name
        self.base_url = base_url
        self.is_nsfw = is_nsfw
        self.headers = {"User-Agent": "Mozilla/5.0"}
        
    # Madara often has different selectors, but for simple MVP let's keep it subclassed
    # and we can override specific methods if needed.

# Note: many of the user's list are actually already mirrors of the ones we have.
