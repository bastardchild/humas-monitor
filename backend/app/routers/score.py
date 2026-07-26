from fastapi import APIRouter, HTTPException
from app.services.scoring_service import ScoringService
from app.core.database import supabase

router = APIRouter(prefix="/score", tags=["Scoring"])

@router.post("/process")
async def process_scoring():
    """Process all unscored raw search results."""
    try:
        summary = await ScoringService.process_unscored_items()
        return {"status": "success", "data": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results")
async def get_scored_results(limit: int = 50):
    """Retrieve top scored results."""
    try:
        data = supabase.table("scored_results").select("*, raw_search_results(title, snippet, keyword)").order("relevance_score", desc=True).limit(limit).execute()
        return {"status": "success", "data": data.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
