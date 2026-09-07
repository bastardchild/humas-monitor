"""One-off: paginate Supabase tables -> SQLite. Run offline before cutover."""
import os, json, sqlite3
from app.core.config import settings
TABLES = ["raw_search_results","instagram_posts","tiktok_posts","cleaned_instagram_captions","scored_results","sentiment_analysis_results"]
def run():
    from supabase import create_client
    supa = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    conn = sqlite3.connect(os.getenv("DATABASE_PATH","./data/app.db"))
    for t in TABLES:
        rows = supa.table(t).select("*").execute().data or []
        print(f"{t}: {len(rows)} rows")
        for r in rows:
            cols = ",".join(r.keys()); ph = ",".join("?"*len(r))
            try: conn.execute(f"INSERT OR REPLACE INTO {t} ({cols}) VALUES ({ph})", tuple(json.dumps(v) if isinstance(v,(dict,list)) else v for v in r.values()))
            except Exception as e: print(f"skip {t}: {e}")
        conn.commit()
    conn.close(); print("done")
if __name__ == "__main__": run()
