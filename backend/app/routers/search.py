import asyncio
import traceback
from fastapi import APIRouter, HTTPException, Query
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