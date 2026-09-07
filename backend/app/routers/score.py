#backend/app/routers/score.py

import asyncio
from fastapi import APIRouter, HTTPException
from app.services.scoring_service import ScoringService
from app.core.db import get_db
import json

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
        with get_db() as db:
            rows = db.execute("SELECT s.*, r.title, r.snippet, r.keyword FROM scored_results s LEFT JOIN raw_search_results r ON r.id=s.raw_id ORDER BY s.score DESC LIMIT ?", (limit,)).fetchall()
            return {"status": "success", "data": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/news")
async def get_scored_news_results(limit: int = 50):
    """Retrieve top scored news results."""
    try:
        with get_db() as db:
            rows = db.execute("SELECT s.*, r.title, r.snippet, r.keyword FROM scored_news_results s LEFT JOIN raw_news_search_results r ON r.id=s.raw_news_id ORDER BY s.score DESC LIMIT ?", (limit,)).fetchall()
            return {"status": "success", "data": [dict(r) for r in rows]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
