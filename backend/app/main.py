from fastapi import FastAPI
from app.core.config import settings
from app.routers import search, score, crawl, clean, sentiment

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(search.router, prefix="/api/v1")
app.include_router(score.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")  # Modul Crawler Baru
app.include_router(clean.router, prefix="/api/v1")
app.include_router(sentiment.router, prefix="/api/v1")  # Register router sentimen

@app.get("/")
def read_root():
    return {"message": "UNMER Monitor API is running"}
