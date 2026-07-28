from fastapi import APIRouter, HTTPException
from app.services.serpapi_service import SerpAPIService

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("/fetch")
async def fetch_search_results():
    """Trigger Google Search via SerpAPI for Instagram UNMER keywords (Last 36h)."""
    try:
        result = await SerpAPIService.fetch_and_store_results()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
