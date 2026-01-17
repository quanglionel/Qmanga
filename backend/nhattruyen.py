"""
NhatTruyen Source - Implementation as NetTruyen Clone
"""

from nettruyen import NetTruyenSource

class NhatTruyenSource(NetTruyenSource):
    """Manga source implementation for NhatTruyen (NetTruyen clone)"""
    
    name = "NhatTruyen"
    base_url = "https://nhattruyenmax.com"
    icon = "https://nhattruyenmax.com/favicon.ico"
    cache_file = "nhattruyen_cache.json"
    
    def __init__(self):
        super().__init__()
        self.headers["Referer"] = f"{self.base_url}/"

nhattruyen = NhatTruyenSource()
