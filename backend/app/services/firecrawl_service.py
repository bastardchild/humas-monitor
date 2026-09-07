# backend/app/services/firecrawl_service.py

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
from firecrawl import Firecrawl

from app.core.config import settings
from app.core.db import get_db
import json

logger = logging.getLogger(__name__)


class FirecrawlService:

    @classmethod
    async def crawl_recent_news_articles(
        cls, 
        hours: int = 48, 
        min_score: float = 50.0
    ) -> Dict[str, Any]:

        with get_db() as db:
            high_score_raw_news_ids = [r[0] for r in db.execute("SELECT raw_news_id FROM scored_news_results WHERE score >= ?", (min_score,)).fetchall()]
        if not high_score_raw_news_ids:
            return {"status":"skipped","message":f"Tidak ada data berita dengan score >= {min_score}.","target_count":0}
        with get_db() as db:
            scraped_raw_ids = {r[0] for r in db.execute("SELECT id FROM news_articles").fetchall()}
            scraped_urls = {r[0] for r in db.execute("SELECT url FROM news_articles").fetchall()}
            ph=",".join("?"*len(high_score_raw_news_ids))
            raw_items=[dict(r) for r in db.execute(f"SELECT id, url, title, snippet FROM raw_news_search_results WHERE id IN ({ph})", tuple(high_score_raw_news_ids)).fetchall()]

        # 4. Filter URL yang belum di-crawl
        targets: List[Dict[str, Any]] = []
        for item in raw_items:
            raw_news_id = item["id"]
            url = item["url"]

            already_scraped = (raw_news_id in scraped_raw_ids) or (url in scraped_urls)

            if not already_scraped:
                targets.append(item)

        if not targets:
            return {
                "status": "skipped",
                "message": f"Semua berita ber-skor >= {min_score} sudah ada di news_articles.",
                "target_count": 0
            }

        # 5. Inisialisasi Firecrawl
        firecrawl_key = getattr(settings, "FIRECRAWL_API_KEY", None)
        if not firecrawl_key:
            raise ValueError("FIRECRAWL_API_KEY belum dikonfigurasi di settings/.env")

        firecrawl_app = Firecrawl(api_key=firecrawl_key)
        semaphore = asyncio.Semaphore(2)

        async def scrape_single_target(item: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                raw_news_id = item["id"]
                url = item["url"]

                try:
                    # PERBAIKAN: Kirim dictionary secara langsung tanpa keyword 'params='                
                    scrape_result = await asyncio.to_thread(
                        firecrawl_app.scrape,
                        url,
                        formats=["markdown"],
                        only_main_content=True,
                    )

                    metadata = getattr(scrape_result, "metadata", None) or {}
                    markdown_content = getattr(scrape_result, "markdown", "") or ""

                    if hasattr(metadata, "model_dump"):
                        metadata = metadata.model_dump()
                    elif not isinstance(metadata, dict):
                        metadata = vars(metadata)

                    payload = {
                        "raw_news_id": raw_news_id,
                        "url": url,
                        "title": metadata.get("title") or item.get("title", ""),
                        "description": metadata.get("description") or item.get("snippet", ""),
                        "content_markdown": markdown_content,
                        "author": metadata.get("author"),
                        "published_at": metadata.get("publishedTime"),
                        "language": metadata.get("language", "id"),
                        "raw_firecrawl_json": scrape_result.model_dump(),
                    }

                    with get_db() as db:
                        db.execute("INSERT OR REPLACE INTO news_articles (url,title,description,content_markdown) VALUES (?,?,?,?)",
                                   (payload["url"], payload["title"], payload["description"], payload["content_markdown"]))
                    await asyncio.sleep(1.0)
                    return {"success": True, "url": url}

                except Exception as e:
                    logger.error(f"[Firecrawl Error] Gagal crawl {url}: {str(e)}", exc_info=True)
                    return {"success": False, "url": url, "error": str(e)}

        results = await asyncio.gather(*(scrape_single_target(item) for item in targets))

        saved_count = sum(1 for r in results if r.get("success"))
        failed_items = [r for r in results if not r.get("success")]

        return {
            "status": "success",
            "min_score": min_score,
            "total_target_urls": len(targets),
            "successfully_scraped": saved_count,
            "failed_count": len(failed_items),
            "failures": failed_items
        }