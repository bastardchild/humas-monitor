# backend/app/routers/crawl.py

from fastapi import APIRouter, HTTPException, Query
from app.services.apify_service import ApifyService

router = APIRouter(prefix="/crawl", tags=["Social Media Crawler"])


@router.post("/instagram")
async def trigger_instagram_crawl(
    hours: int = Query(default=48, ge=1, le=168, description="Rentang jam postingan yang akan di-crawl"),
    min_score: float = Query(default=50.0, ge=0.0, le=100.0, description="Minimum relevance score untuk di-crawl")
):
    """
    Trigger Apify Instagram Post Scraper hanya untuk postingan Instagram
    yang memiliki relevance_score >= min_score (default: 50.0).
    """
    try:
        result = await ApifyService.crawl_recent_instagram_posts(hours=hours, min_score=min_score)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tiktok")
async def trigger_tiktok_crawl(
    hours: int = Query(default=48, ge=1, le=168, description="Rentang jam postingan yang akan di-crawl"),
    min_score: float = Query(default=50.0, ge=0.0, le=100.0, description="Minimum relevance score untuk di-crawl")
):
    """
    Trigger Apify TikTok Scraper (clockworks/tiktok-scraper) hanya untuk postingan TikTok
    yang memiliki relevance_score >= min_score (default: 50.0).
    """
    try:
        result = await ApifyService.crawl_recent_tiktok_posts(hours=hours, min_score=min_score)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))