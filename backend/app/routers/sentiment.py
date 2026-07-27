# backend/app/routers/sentiment.py

from fastapi import APIRouter, HTTPException, Query
from app.services.sentiment_service import SentimentService

router = APIRouter(prefix="/sentiment", tags=["Sentiment Analysis"])

@router.post("/analyze")
async def analyze_sentiment(
    batch_size: int = Query(default=15, ge=1, le=50, description="Jumlah postingan per request API DeepSeek (untuk hemat token)")
):
    """
    Analisis sentimen caption & engagement postingan Instagram
    yang belum diolah menggunakan DeepSeek API (diurutkan dari yang terbaru).
    """
    try:
        result = await SentimentService.analyze_unprocessed_captions(batch_size=batch_size)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
