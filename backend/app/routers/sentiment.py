# backend/app/routers/sentiment.py

from fastapi import APIRouter, HTTPException, Query
from app.services.sentiment_service import SentimentService

router = APIRouter(prefix="/sentiment", tags=["Sentiment Analysis"])


@router.post("/instagram")
async def analyze_instagram_sentiment(
    batch_size: int = Query(
        default=15, 
        ge=1, 
        le=50, 
        description="Jumlah postingan Instagram per request ke LLM (untuk efisiensi token)"
    )
):
    """
    Analisis sentimen caption & engagement postingan Instagram
    yang belum diolah menggunakan AI (DeepSeek / Gemini).
    """
    try:
        result = await SentimentService.analyze_unprocessed_instagram_captions(batch_size=batch_size)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tiktok")
async def analyze_tiktok_sentiment(
    batch_size: int = Query(
        default=15, 
        ge=1, 
        le=50, 
        description="Jumlah postingan TikTok per request ke LLM (untuk efisiensi token)"
    )
):
    """
    Analisis sentimen caption & engagement postingan TikTok
    yang belum diolah menggunakan AI (DeepSeek / Gemini).
    """
    try:
        result = await SentimentService.analyze_unprocessed_tiktok_captions(batch_size=batch_size)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_all_sentiment(
    batch_size: int = Query(
        default=15, 
        ge=1, 
        le=50, 
        description="Jumlah postingan per platform per request ke LLM"
    )
):
    """
    Analisis sentimen caption & engagement untuk SEMUA platform (Instagram & TikTok) sekaligus.
    """
    try:
        result = await SentimentService.analyze_all_unprocessed(batch_size=batch_size)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))