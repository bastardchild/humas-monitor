import httpx
from typing import List, Dict, Any
from app.core.config import settings
from app.core.database import supabase

KEYWORDS = [
    "site:instagram.com universitas merdeka malang",
    "site:instagram.com unmer malang",
    "site:tiktok.com unmer malang",
    "site:tiktok.com universitas merdeka malang"    
]

class SerpAPIService:
    SERPAPI_URL = "https://serpapi.com/search.json"

    @classmethod
    async def fetch_and_store_results(cls) -> Dict[str, Any]:
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

                    # Insert raw result into Supabase (Skip duplicate URLs)
                    payload = {
                        "keyword": kw,
                        "url": url,
                        "title": item.get("title", ""),
                        "snippet": item.get("snippet", ""),
                        "raw_json": item
                    }

                    try:
                        # Attempt upsert/insert with ignore_duplicates
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
