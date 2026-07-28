# backend/app/services/scoring_service.py

import re
from typing import List, Dict, Any
from app.core.database import supabase
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


class ScoringService:
    @classmethod
    async def process_unscored_items(cls) -> Dict[str, Any]:
        # Query rows where id NOT IN (scored_results) or not yet scored
        scored_resp = supabase.table("scored_results").select("raw_id").not_.is_("scored_at", "null").execute()
        scored_ids = [row["raw_id"] for row in scored_resp.data] if scored_resp.data else []

        # Fetch unscored records from raw_search_results
        query = supabase.table("raw_search_results").select("*")
        if scored_ids:
            query = query.not_.in_("id", scored_ids)
        
        unscored_rows = query.execute().data or []
        processed_count = 0

        for row in unscored_rows:
            raw_id = row["id"]
            url = row["url"]
            title = row.get("title") or ""
            snippet = row.get("snippet") or ""

            score, breakdown = UnmerScorer.calculate_score(title, snippet, url)

            score_payload = ScoreOutput(
                raw_id=raw_id,
                url=url,
                relevance_score=score,
                scoring_details=breakdown
            )

            # Save to scored_results
            supabase.table("scored_results").upsert(
                {
                    "raw_id": score_payload.raw_id,
                    "url": score_payload.url,
                    "relevance_score": score_payload.relevance_score,
                    "scoring_details": score_payload.scoring_details.model_dump()
                },
                on_conflict="raw_id"
            ).execute()

            processed_count += 1

        return {
            "unscored_items_found": len(unscored_rows),
            "successfully_scored": processed_count
        }