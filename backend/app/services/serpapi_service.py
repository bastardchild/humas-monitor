import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.database import supabase
from datetime import datetime, timedelta

KEYWORDS = [
    "site:instagram.com universitas merdeka malang",
    "site:instagram.com unmer malang",
    "site:tiktok.com unmer malang",
    "site:tiktok.com universitas merdeka malang"    
]

NEWS_KEYWORDS = [
    "universitas merdeka malang"
]

class SerpAPIService:
    SERPAPI_URL = "https://serpapi.com/search.json"

    @classmethod
    async def fetch_and_store_results(cls) -> Dict[str, Any]:
        """Menyimpan pencarian sosmed ke tabel 'raw_search_results'"""
        total_fetched = 0
        total_saved = 0
        duplicates_skipped = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            for kw in KEYWORDS:
                params = {
                    "engine": "google",
                    "q": kw,
                    "api_key": settings.SERPAPI_KEY,
                    "num": 100,            # Up to 100 results
                    "tbs": "qdr:d3",        # Published within last 36 hours (3 days)
                    "hl": "id",            # Bahasa Indonesia
                    "gl": "id"             # Location: Indonesia
                }
                
                response = await client.get(cls.SERPAPI_URL, params=params)
                if response.status_code != 200:
                    continue
                
                data = response.json()
                organic_results = data.get("organic_results", [])
                total_fetched += len(organic_results)

                for item in organic_results:
                    url = item.get("link")
                    if not url:
                        continue

                    payload = {
                        "keyword": kw,
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "raw_json": item
                    }

                    try:
                        # Masuk ke tabel raw_search_results (Sosmed)
                        res = supabase.table("raw_search_results").insert(payload).execute()
                        if res.data:
                            total_saved += 1
                    except Exception:
                        duplicates_skipped += 1

        return {
            "total_fetched": total_fetched,
            "total_saved_new": total_saved,
            "duplicates_skipped": duplicates_skipped
        }

    @classmethod
    async def fetch_and_store_news_results(cls) -> Dict[str, Any]:
        """Menyimpan pencarian berita ke tabel 'raw_news_search_results'"""
        total_fetched = 0
        total_saved = 0
        duplicates_skipped = 0

        # Naikkan timeout menjadi 60 detik agar tidak ReadTimeout
        async with httpx.AsyncClient(timeout=60.0) as client:
            for kw in NEWS_KEYWORDS:
                after = (datetime.utcnow() - timedelta(days=3)).strftime("%Y-%m-%d")            

                params = {
                    "engine": "google",
                    "tbm": "nws",
                    "q": f'universitas merdeka malang after:{after}',
                    "hl": "id",
                    "gl": "id",
                    "num": 30,
                    "api_key": settings.SERPAPI_KEY,
                }

                response = await client.get(cls.SERPAPI_URL, params=params)
                if response.status_code != 200:
                    continue

                data = response.json()
                news_results = data.get("news_results", [])
                total_fetched += len(news_results)

                for item in news_results:
                    url = item.get("link")
                    if not url:
                        continue

                    payload = {
                        "keyword": kw,
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "raw_json": item
                    }

                    try:
                        res = supabase.table("raw_news_search_results").insert(payload).execute()
                        if res.data:
                            total_saved += 1
                    except Exception:
                        duplicates_skipped += 1

        return {
            "total_fetched": total_fetched,
            "total_saved_new": total_saved,
            "duplicates_skipped": duplicates_skipped
        }

    # @classmethod
    # async def fetch_and_store_google_reviews(cls, place_id: str = "ChIJj7qtWSso1i0RvE-S5MXstO0") -> Dict[str, Any]:
    #     """Menyimpan ulasan Google Maps ke tabel 'raw_google_reviews'"""
    #     total_fetched = 0
    #     total_saved = 0
    #     duplicates_skipped = 0

    #     async with httpx.AsyncClient(timeout=60.0) as client:
    #         params = {
    #             "engine": "google_maps_reviews",
    #             "place_id": place_id,
    #             "api_key": settings.SERPAPI_KEY,
    #             "hl": "id",
    #             "sort_by": "newestFirst",
    #             "num": 15  # Mengatur jumlah hasil menjadi 10 ulasan terbaru
    #         }

    #         response = await client.get(cls.SERPAPI_URL, params=params)
    #         if response.status_code != 200:
    #             return {
    #                 "total_fetched": 0,
    #                 "total_saved_new": 0,
    #                 "duplicates_skipped": 0,
    #                 "error": f"Failed with status code {response.status_code}"
    #             }

    #         data = response.json()
    #         reviews = data.get("reviews", [])
    #         total_fetched += len(reviews)

    #         for item in reviews:
    #             review_id = item.get("review_id")
    #             if not review_id:
    #                 continue

    #             user_info = item.get("user", {})
    #             payload = {
    #                 "place_id": place_id,
    #                 "review_id": review_id,
    #                 "author_name": user_info.get("name", ""),
    #                 "rating": item.get("rating"),
    #                 "snippet": item.get("snippet", ""),
    #                 "raw_json": item
    #             }

    #             try:
    #                 # Masuk ke tabel raw_google_reviews
    #                 res = supabase.table("raw_google_reviews").insert(payload).execute()
    #                 if res.data:
    #                     total_saved += 1
    #             except Exception:
    #                 duplicates_skipped += 1

    #     return {
    #         "total_fetched": total_fetched,
    #         "total_saved_new": total_saved,
    #         "duplicates_skipped": duplicates_skipped
    #     }

    @classmethod
    async def fetch_and_store_google_reviews(cls, place_id: str = "ChIJj7qtWSso1i0RvE-S5MXstO0") -> Dict[str, Any]:
        """Menyimpan ulasan Google Maps ke tabel 'raw_google_reviews'"""
        total_fetched = 0
        total_saved = 0
        duplicates_skipped = 0

        async with httpx.AsyncClient(timeout=60.0) as client:
            params = {
                "engine": "google_maps_reviews",
                "place_id": place_id,
                "api_key": settings.SERPAPI_KEY,
                "hl": "id",
                "sort_by": "newestFirst",
            }

            response = await client.get(cls.SERPAPI_URL, params=params)
            
            if response.status_code != 200:
                try:
                    error_json = response.json()
                    error_message = error_json.get("error", response.text)
                except Exception:
                    error_message = response.text

                return {
                    "total_fetched": 0,
                    "total_saved_new": 0,
                    "duplicates_skipped": 0,
                    "error": f"SerpAPI Error ({response.status_code}): {error_message}"
                }

            data = response.json()
            reviews = data.get("reviews", [])
            total_fetched += len(reviews)

            for item in reviews:
                review_id = item.get("review_id")
                if not review_id:
                    continue

                user_info = item.get("user", {})
                payload = {
                    "review_id": review_id,
                    "author_name": user_info.get("name", ""),
                    "rating": item.get("rating"),
                    "snippet": item.get("snippet", ""),
                    "raw_json": item
                }

                try:
                    # Menggunakan UPSERT dengan on_conflict agar tidak crash saat review_id sudah ada
                    res = supabase.table("raw_google_reviews").upsert(
                        payload, 
                        on_conflict="review_id"
                    ).execute()
                    
                    if res.data:
                        total_saved += 1
                except Exception as e:
                    # Catat sebagai duplikat / dilewati tanpa memicu 'raise' (agar tidak HTTP 500)
                    print(f"SKIPPED/ERROR saving review {review_id}: {e}")
                    duplicates_skipped += 1

        return {
            "total_fetched": total_fetched,
            "total_saved_new": total_saved,
            "duplicates_skipped": duplicates_skipped
        }