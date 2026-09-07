import asyncio
import json
import traceback
from fastapi import APIRouter, HTTPException, Query
from app.core.db import get_db
from app.services.serpapi_service import SerpAPIService

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("/fetch/social")
async def fetch_social_results():
    """Trigger pencarian sosmed (Instagram/TikTok) via SerpAPI."""
    try:
        result = await SerpAPIService.fetch_and_store_results()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch/news")
async def fetch_news_results():
    """Trigger pencarian berita (Google News tbm=nws) via SerpAPI."""
    try:
        result = await SerpAPIService.fetch_and_store_news_results()
        return {"status": "success", "data": result}
    except Exception as e:
        print("ERROR FETCH NEWS:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=repr(e))

@router.post("/fetch/reviews")
async def fetch_google_reviews(place_id: str = Query("ChIJj7qtWSso1i0RvE-S5MXstO0", description="Google Places ID")):
    """Trigger pengambilan ulasan Google Maps via SerpAPI."""
    try:
        result = await SerpAPIService.fetch_and_store_google_reviews(place_id)
        return {"status": "success", "data": result}
    except Exception as e:
        print("ERROR FETCH REVIEWS:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=repr(e))

@router.get("/reviews")
async def get_google_reviews(limit: int = 100):
    try:
        with get_db() as db:
            rows=[dict(r) for r in db.execute("SELECT * FROM raw_google_reviews ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]
            # raw_json contains review data; parse for frontend
            out=[]
            for r in rows:
                try:
                    j=json.loads(r.get("review_json") or r.get("raw_json") or "{}") if isinstance(r.get("review_json") or r.get("raw_json"), str) else (r.get("review_json") or r.get("raw_json") or {})
                except: j={}
                # j may be the payload dict itself
                out.append({
                    "id": r["id"],
                    "author_name": j.get("author_name") or r.get("author_name") or "Anonymous",
                    "rating": j.get("rating") if j.get("rating") is not None else r.get("rating"),
                    "snippet": j.get("snippet") or r.get("snippet") or "",
                    "review_id": j.get("review_id") or r.get("review_id") or str(r["id"]),
                    "created_at": r.get("created_at"),
                    "raw": j
                })
            return {"status":"success","data":out}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fetch/all")
async def fetch_all_results():
    """Trigger pencarian sosmed, berita, dan ulasan Google Maps sekaligus secara paralel."""
    try:
        social_res, news_res, reviews_res = await asyncio.gather(
            SerpAPIService.fetch_and_store_results(),
            SerpAPIService.fetch_and_store_news_results(),
            SerpAPIService.fetch_and_store_google_reviews()
        )
        return {
            "status": "success",
            "data": {
                "social": social_res,
                "news": news_res,
                "reviews": reviews_res
            }
        }
    except Exception as e:
        print("ERROR FETCH ALL:", traceback.format_exc())
        raise HTTPException(status_code=500, detail=repr(e))