from fastapi import FastAPI
from app.core.config import settings
from app.routers import search, score, crawl

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(search.router, prefix="/api/v1")
app.include_router(score.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")  # Modul Crawler Baru

@app.get("/")
def read_root():
    return {"message": "UNMER Monitor API is running"}
