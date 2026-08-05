#backend/app/routers/score.py

import asyncio
from fastapi import APIRouter, HTTPException
from app.services.scoring_service import ScoringService
from app.core.database import supabase

router = APIRouter(prefix="/score", tags=["Scoring"])

# --- PROCESS SCORING ENDPOINTS ---

@router.post("/process/social")
async def process_social_scoring():
    """Process all unscored social media raw search results."""
    try:
        summary = await ScoringService.process_unscored_social_items()
        return {"status": "success", "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process/news")
async def process_news_scoring():
    """Process all unscored news search results."""
    try:
        summary = await ScoringService.process_unscored_news_items()
        return {"status": "success", "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process/all")
async def process_all_scoring():
    """Process unscored social media and news results concurrently."""
    try:
        social_res, news_res = await asyncio.gather(
            ScoringService.process_unscored_social_items(),
            ScoringService.process_unscored_news_items()
        )
        return {
            "status": "success",
            "data": {
                "social": social_res,
                "news": news_res
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- GET RESULTS ENDPOINTS ---

@router.get("/results/social")
async def get_scored_social_results(limit: int = 50):
    """Retrieve top scored social media results."""
    try:
        data = (
            supabase.table("scored_results")
            .select("*, raw_search_results(title, snippet, keyword)")
            .order("relevance_score", desc=True)
            .limit(limit)
            .execute()
        )
        return {"status": "success", "data": data.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/news")
async def get_scored_news_results(limit: int = 50):
    """Retrieve top scored news results."""
    try:
        data = (
            supabase.table("scored_news_results")
            .select("*, raw_news_search_results(title, snippet, keyword)")
            .order("relevance_score", desc=True)
            .limit(limit)
            .execute()
        )
        return {"status": "success", "data": data.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
