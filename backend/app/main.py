from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.routers import search, score, crawl, clean, sentiment, dashboard

from app.core.db import init_db
init_db()

app = FastAPI(title=settings.PROJECT_NAME)

static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/health/db")
def health_db():
    from app.core.db import DB_PATH
    import sqlite3
    try:
        c = sqlite3.connect(str(DB_PATH)); cur = c.execute("SELECT count(*) FROM sqlite_master"); n = cur.fetchone()[0]; c.close()
        return {"ok": True, "db_path": str(DB_PATH), "tables": n}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Include UI / Dashboard Router (HTMX & Alpine.js)
app.include_router(dashboard.router)

# Include API v1 Routers
app.include_router(search.router, prefix="/api/v1")
app.include_router(score.router, prefix="/api/v1")
app.include_router(crawl.router, prefix="/api/v1")
app.include_router(clean.router, prefix="/api/v1")
app.include_router(sentiment.router, prefix="/api/v1")
