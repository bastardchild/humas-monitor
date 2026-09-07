from fastapi import FastAPI
from app.core.config import settings
from app.routers import search, score, crawl, clean, sentiment

from app.core.db import init_db
init_db()

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/health/db")
def health_db():
    from app.core.db import DB_PATH
    import sqlite3
    try:
        c = sqlite3.connect(str(DB_PATH)); cur = c.execute("SELECT count(*) FROM sqlite_master"); n = cur.fetchone()[0]; c.close()
        return {"ok": True, "db_path": str(DB_PATH), "tables": n}
    except Exception as e:
        return {"ok": False, "error": str(e)}

app.include_router(search.router, prefix="/api/v1")
app.include_router(score.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")  # Modul Crawler Baru
app.include_router(clean.router, prefix="/api/v1")
app.include_router(sentiment.router, prefix="/api/v1")  # Register router sentimen

@app.get("/")
def read_root():
    return {"message": "UNMER Monitor API is running"}
