# backend/app/services/scoring_service.py

import re
from typing import List, Dict, Any
from app.core.db import get_db
import json
from app.models.schemas import ScoreOutput, ScoringBreakdown


class UnmerScorer:
    """Rule-based Pydantic scoring system for Universitas Merdeka Malang."""

    # List pola kata kunci / hashtag kampus lain di Malang
    OTHER_MALANG_CAMPUSES = [
        # Universitas Negeri Malang (UM)
        r"\buniversitas negeri malang\b",
        r"\b#universitasnegerimalang\b",
        r"\b#pkkmbum\d*\b",
        r"\b#mahasiswaum\b",
        r"\b#mabaum\b",
        # Universitas Brawijaya (UB)
        r"\buniversitas brawijaya\b",
        r"\b#universitasbrawijaya\b",
        r"\b#mahasiswaub\b",
        r"\b#ubmalang\b",
        # Universitas Muhammadiyah Malang (UMM)
        r"\buniversitas muhammadiyah malang\b",
        r"\b#universitasmuhammadiyahmalang\b",
        r"\b#umm\b",
        r"\b#ummmalang\b",
        # Politeknik Negeri Malang (POLINEMA)
        r"\bpoliteknik negeri malang\b",
        r"\b#polinema\b",
        r"\b#polinemamalang\b",
        # UIN Malang & Unisma
        r"\buin maulana malik ibrahim\b",
        r"\buin malang\b",
        r"\buniversitas islam malang\b",
        r"\b#unisma\b",
    ]

    @staticmethod
    def calculate_score(title: str, snippet: str, url: str) -> tuple[float, ScoringBreakdown]:
        text = f"{title} {snippet} {url}".lower()

        # 1. Cek apakah ada penyebutan nama UNMER secara eksplisit
        has_unmer_kw = "unmer" in text or "universitas merdeka" in text

        # 2. Cek apakah teks mengandung indikator kampus lain di Malang
        has_other_campus = any(
            re.search(pattern, text) for pattern in UnmerScorer.OTHER_MALANG_CAMPUSES
        )

        # Jika murni membahas kampus lain TANPA sebut UNMER -> Diskualifikasi (Skor 0)
        if has_other_campus and not has_unmer_kw:
            breakdown = ScoringBreakdown(
                exact_match_found=False,
                unmer_malang_match=False,
                unmer_keyword_match=False,
                malang_context_match=False,
                base_points=0,
                matched_terms=["disqualified: detected other malang campus"]
            )
            return 0.0, breakdown

        # 3. Hitung skor normal jika lolos filter
        matched_terms = []
        points = 0

        exact_match = "universitas merdeka malang" in text
        unmer_malang = "unmer malang" in text
        unmer_kw = "unmer" in text
        malang_ctx = "malang" in text

        if exact_match:
            points += 50
            matched_terms.append("universitas merdeka malang")
        if unmer_malang:
            points += 30
            matched_terms.append("unmer malang")
        if unmer_kw:
            points += 10
            matched_terms.append("unmer")
        if malang_ctx:
            points += 10
            matched_terms.append("malang")

        final_score = float(min(points, 100))

        breakdown = ScoringBreakdown(
            exact_match_found=exact_match,
            unmer_malang_match=unmer_malang,
            unmer_keyword_match=unmer_kw,
            malang_context_match=malang_ctx,
            base_points=points,
            matched_terms=matched_terms
        )

        return final_score, breakdown

class UnmerFullTextScorer:
    """Scorer Layer 2 untuk mengevaluasi teks lengkap artikel hasil crawling Firecrawl."""

    @staticmethod
    def calculate_l2_score(
        title: str, 
        description: str, 
        content_markdown: str, 
        url: str
    ) -> tuple[float, Dict[str, Any]]:
        full_text = f"{title} {description} {content_markdown} {url}".lower()
        content_lower = (content_markdown or "").lower()
        title_lower = (title or "").lower()

        # 1. Filter Diskualifikasi Utuh (Jika didominasi kampus lain TANPA sebut UNMER)
        has_unmer_kw = "unmer" in full_text or "universitas merdeka" in full_text
        has_other_campus = any(
            re.search(pattern, full_text) for pattern in UnmerScorer.OTHER_MALANG_CAMPUSES
        )

        if has_other_campus and not has_unmer_kw:
            return 0.0, {
                "disqualified": True,
                "reason": "Murni membahas kampus lain tanpa menyebut UNMER"
            }

        points = 0
        matched_terms = []

        # 2. Penilaian Judul Artikel (Bobot 40 Poin)
        if "universitas merdeka malang" in title_lower:
            points += 40
            matched_terms.append("title: universitas merdeka malang")
        elif "unmer" in title_lower:
            points += 25
            matched_terms.append("title: unmer")

        # 3. Penilaian Lead Paragraph / 500 Karakter Pertama (Bobot 30 Poin)
        lead_text = content_lower[:500]
        if "universitas merdeka malang" in lead_text or "unmer malang" in lead_text:
            points += 30
            matched_terms.append("lead_paragraph: exact/unmer malang match")
        elif "unmer" in lead_text:
            points += 15
            matched_terms.append("lead_paragraph: unmer match")

        # 4. Kerapatan / Frekuensi Kemunculan dalam Bodi Artikel (Bobot 20 Poin)
        exact_count = content_lower.count("universitas merdeka malang")
        unmer_count = content_lower.count("unmer")

        if exact_count >= 2 or unmer_count >= 4:
            points += 20
            matched_terms.append(f"high_density (exact:{exact_count}, unmer:{unmer_count})")
        elif exact_count >= 1 or unmer_count >= 1:
            points += 10
            matched_terms.append(f"low_density (exact:{exact_count}, unmer:{unmer_count})")

        # 5. Konteks Lokasi Malang (Bobot 10 Poin)
        if "malang" in full_text:
            points += 10
            matched_terms.append("context: malang")

        final_score = float(min(points, 100))
        details = {
            "base_points": points,
            "matched_terms": matched_terms,
            "exact_occurrences": exact_count,
            "unmer_occurrences": unmer_count
        }

        return final_score, details

class ScoringService:
    @classmethod
    async def process_unscored_social_items(cls) -> Dict[str, Any]:
        with get_db() as db:
            scored_ids = {r[0] for r in db.execute("SELECT raw_id FROM scored_results").fetchall()}
            if scored_ids:
                placeholders = ",".join("?"*len(scored_ids))
                unscored = db.execute(f"SELECT * FROM raw_search_results WHERE id NOT IN ({placeholders})", tuple(scored_ids)).fetchall()
            else:
                unscored = db.execute("SELECT * FROM raw_search_results").fetchall()
            unscored_rows = [dict(r) for r in unscored]
            count = 0
            for row in unscored_rows:
                score, breakdown = UnmerScorer.calculate_score(row.get("title") or "", row.get("snippet") or "", row["url"])
                db.execute("INSERT OR REPLACE INTO scored_results (raw_id,score,scoring_details) VALUES (?,?,?)",
                           (row["id"], score, json.dumps(breakdown.model_dump())))
                count += 1
            return {"unscored_items_found": len(unscored_rows), "successfully_scored": count}

    @classmethod
    async def process_unscored_news_items(cls) -> Dict[str, Any]:
        with get_db() as db:
            scored_ids = {r[0] for r in db.execute("SELECT raw_news_id FROM scored_news_results").fetchall()}
            if scored_ids:
                placeholders = ",".join("?"*len(scored_ids))
                unscored = db.execute(f"SELECT * FROM raw_news_search_results WHERE id NOT IN ({placeholders})", tuple(scored_ids)).fetchall()
            else:
                unscored = db.execute("SELECT * FROM raw_news_search_results").fetchall()
            rows = [dict(r) for r in unscored]
            count = 0
            for row in rows:
                score, breakdown = UnmerScorer.calculate_score(row.get("title") or "", row.get("snippet") or "", row["url"])
                db.execute("INSERT OR REPLACE INTO scored_news_results (raw_news_id,score,scoring_details) VALUES (?,?,?)",
                           (row["id"], score, json.dumps(breakdown.model_dump())))
                count += 1
            return {"unscored_items_found": len(rows), "successfully_scored": count}

    @classmethod
    async def process_unscored_crawled_news_articles(cls) -> Dict[str, Any]:
        with get_db() as db:
            scored_ids = {r[0] for r in db.execute("SELECT id FROM scored_news_articles_l2").fetchall()}
            if scored_ids:
                placeholders = ",".join("?"*len(scored_ids))
                unscored = db.execute(f"SELECT id,url,title,description,content_markdown FROM news_articles WHERE id NOT IN ({placeholders})", tuple(scored_ids)).fetchall()
            else:
                unscored = db.execute("SELECT id,url,title,description,content_markdown FROM news_articles").fetchall()
            rows = [dict(r) for r in unscored]
            count = 0
            for row in rows:
                score_l2, details = UnmerFullTextScorer.calculate_l2_score(row.get("title") or "", row.get("description") or "", row.get("content_markdown") or "", row["url"])
                db.execute("INSERT OR REPLACE INTO scored_news_articles_l2 (id,url,score) VALUES (?,?,?)", (row["id"], row["url"], score_l2))
                count += 1
            return {"unscored_crawled_articles_found": len(rows), "successfully_scored_l2": count}