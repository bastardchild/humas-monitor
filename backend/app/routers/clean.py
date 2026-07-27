# backend/app/routers/clean.py

from fastapi import APIRouter, HTTPException
from app.services.cleaning_service import CleaningService

router = APIRouter(prefix="/clean", tags=["Data Cleaning"])

@router.post("/captions")
async def clean_instagram_captions():
    """
    Proses dan bersihkan field caption dari tabel instagram_posts
    yang belum terdaftar di tabel cleaned_instagram_captions.
    """
    try:
        result = await CleaningService.process_uncleaned_captions()
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))