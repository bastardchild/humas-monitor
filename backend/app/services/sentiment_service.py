# backend/app/services/sentiment_service.py

import json
import httpx
from typing import Dict, Any, List
from app.core.config import settings
from app.core.database import supabase


class SentimentService:

    SYSTEM_PROMPT = """
Anda adalah sistem AI analisis sentimen institusi Universitas Merdeka Malang (UNMER).
Tugas Anda adalah menganalisis kumpulan postingan media sosial (Instagram/TikTok) berbasis JSON:

INSTRUKSI BAHASA (SANGAT PENTING):
- WAJIB menggunakan BAHASA INDONESIA untuk seluruh isi teks pada field "reasoning" dan "engagement_context".

TUGAS ANALISIS:
1. Klasifikasikan sentimen caption sebagai: "positive", "neutral", atau "negative".
2. Hitung confidence sentiment_score antara 0 hingga 100.
3. Evaluasi metrik engagement (likes, comments, views/shares jika ada) sebagai bagian konteks engagement dalam Bahasa Indonesia (contoh: "Keterlibatan tinggi", "Respon rendah", "Keterlibatan negatif tinggi").
4. Berikan reasoning singkat maksimal 1 kalimat dalam Bahasa Indonesia.

Tanggapi HANYA dengan format JSON valid sesuai skema ini:
{
  "results": [
    {
      "post_id": 123,
      "cleaned_caption_id": 456,
      "sentiment": "positive|neutral|negative",
      "sentiment_score": 85,
      "reasoning": "Alasan singkat sentimen dalam Bahasa Indonesia.",
      "engagement_context": "Evaluasi singkat metrik engagement dalam Bahasa Indonesia."
    }
  ]
}
"""

    @classmethod
    async def _call_deepseek(cls, user_prompt: str) -> Dict[str, Any]:
        """Panggilan API ke DeepSeek"""
        if not settings.DEEPSEEK_API_KEY:
            raise ValueError("DEEPSEEK_API_KEY belum dikonfigurasi di file .env")

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.DEEPSEEK_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": settings.DEEPSEEK_MODEL,
                    "messages": [
                        {"role": "system", "content": cls.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1
                }
            )

            if response.status_code != 200:
                raise Exception(f"DeepSeek API Error [{response.status_code}]: {response.text}")

            ai_response = response.json()
            raw_content = ai_response["choices"][0]["message"]["content"]
            return json.loads(raw_content)

    @classmethod
    async def _call_gemini(cls, user_prompt: str) -> Dict[str, Any]:
        """Panggilan API ke Gemini API (Google AI Studio)"""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY belum dikonfigurasi di file .env")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.GEMINI_MODEL}:generateContent?key={settings.GEMINI_API_KEY}"

        payload = {
            "systemInstruction": {
                "parts": [{"text": cls.SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code != 200:
                raise Exception(f"Gemini API Error [{response.status_code}]: {response.text}")

            ai_response = response.json()
            raw_content = ai_response["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_content)

    @classmethod
    async def _execute_llm(cls, user_prompt: str) -> Dict[str, Any]:
        """Router eksekusi LLM berdasarkan provider yang dikonfigurasi."""
        provider = settings.LLM_PROVIDER.lower()
        if provider == "gemini":
            return await cls._call_gemini(user_prompt), provider
        elif provider == "deepseek":
            return await cls._call_deepseek(user_prompt), provider
        else:
            raise ValueError(f"LLM_PROVIDER '{provider}' tidak dikenali. Gunakan 'deepseek' atau 'gemini'.")

    @classmethod
    async def analyze_unprocessed_instagram_captions(cls, batch_size: int = 15) -> Dict[str, Any]:
        """Menganalisis sentimen postingan Instagram."""
        analyzed_res = (
            supabase.table("sentiment_analysis_results")
            .select("instagram_post_id")
            .execute()
        )
        analyzed_post_ids = {
            row["instagram_post_id"] 
            for row in (analyzed_res.data or []) 
            if row.get("instagram_post_id")
        }

        query = (
            supabase.table("cleaned_instagram_captions")
            .select("id, instagram_post_id, cleaned_caption, cleaned_at, instagram_posts(likes_count, comments_count)")
            .eq("has_unmer_keyword", True)
            .order("cleaned_at", desc=True)
        )

        if analyzed_post_ids:
            query = query.not_.in_("instagram_post_id", list(analyzed_post_ids))

        unprocessed_rows = query.execute().data or []

        if not unprocessed_rows:
            return {
                "platform": "instagram",
                "status": "skipped",
                "message": "Semua data caption Instagram sudah dianalisis sentimennya.",
                "processed_count": 0
            }

        batch_items = unprocessed_rows[:batch_size]
        payload_posts: List[Dict[str, Any]] = []

        for row in batch_items:
            ig_post = row.get("instagram_posts") or {}
            payload_posts.append({
                "post_id": row["instagram_post_id"],
                "cleaned_caption_id": row["id"],
                "caption": row.get("cleaned_caption", ""),
                "likes_count": ig_post.get("likes_count", 0),
                "comments_count": ig_post.get("comments_count", 0)
            })

        user_prompt = f"Analisis sentimen & engagement Instagram berikut:\n{json.dumps(payload_posts, ensure_ascii=False)}"
        parsed_data, provider = await cls._execute_llm(user_prompt)

        saved_count = 0
        results_list = parsed_data.get("results", [])

        for item in results_list:
            post_id = item.get("post_id") or item.get("instagram_post_id")
            caption_id = item.get("cleaned_caption_id")

            if not post_id or not caption_id:
                continue

            record = {
                "instagram_post_id": post_id,
                "cleaned_caption_id": caption_id,
                "sentiment": str(item.get("sentiment", "neutral")).lower(),
                "sentiment_score": float(item.get("sentiment_score", 50.0)),
                "reasoning": item.get("reasoning", ""),
                "engagement_context": item.get("engagement_context", ""),
                "raw_ai_json": item
            }

            try:
                supabase.table("sentiment_analysis_results").upsert(
                    record, on_conflict="instagram_post_id"
                ).execute()
                saved_count += 1
            except Exception as e:
                print(f"[SentimentService Error IG] Gagal simpan post_id {post_id}: {e}")

        return {
            "platform": "instagram",
            "status": "success",
            "provider_used": provider,
            "batch_size_requested": batch_size,
            "unprocessed_remaining": len(unprocessed_rows) - saved_count,
            "analyzed_and_saved": saved_count
        }

    @classmethod
    async def analyze_unprocessed_tiktok_captions(cls, batch_size: int = 15) -> Dict[str, Any]:
        """Menganalisis sentimen postingan TikTok berdasarkan skema presisi database Supabase."""
        analyzed_res = (
            supabase.table("tiktok_sentiment_analysis_results")
            .select("tiktok_post_id")
            .execute()
        )
        analyzed_post_ids = {
            row["tiktok_post_id"] 
            for row in (analyzed_res.data or []) 
            if row.get("tiktok_post_id")
        }

        # Query join menggunakan nama kolom yang tepat sesuai skema
        query = (
            supabase.table("cleaned_tiktok_captions")
            .select("id, tiktok_post_id, cleaned_caption, cleaned_at, tiktok_posts(likes_count, comments_count, plays_count, shares_count)")
            .eq("has_unmer_keyword", True)
            .order("cleaned_at", desc=True)
        )

        if analyzed_post_ids:
            query = query.not_.in_("tiktok_post_id", list(analyzed_post_ids))

        unprocessed_rows = query.execute().data or []

        if not unprocessed_rows:
            return {
                "platform": "tiktok",
                "status": "skipped",
                "message": "Semua data caption TikTok sudah dianalisis sentimennya.",
                "processed_count": 0
            }

        batch_items = unprocessed_rows[:batch_size]
        payload_posts: List[Dict[str, Any]] = []

        for row in batch_items:
            tt_post = row.get("tiktok_posts") or {}
            payload_posts.append({
                "post_id": row["tiktok_post_id"],
                "cleaned_caption_id": row["id"],
                "caption": row.get("cleaned_caption", ""),
                "likes_count": tt_post.get("likes_count", 0),
                "comments_count": tt_post.get("comments_count", 0),
                "plays_count": tt_post.get("plays_count", 0),
                "shares_count": tt_post.get("shares_count", 0)
            })

        user_prompt = f"Analisis sentimen & engagement TikTok berikut:\n{json.dumps(payload_posts, ensure_ascii=False)}"
        parsed_data, provider = await cls._execute_llm(user_prompt)

        saved_count = 0
        results_list = parsed_data.get("results", [])

        for item in results_list:
            post_id = item.get("post_id") or item.get("tiktok_post_id")
            caption_id = item.get("cleaned_caption_id")

            if not post_id or not caption_id:
                continue

            record = {
                "tiktok_post_id": post_id,
                "cleaned_caption_id": caption_id,
                "sentiment": str(item.get("sentiment", "neutral")).lower(),
                "sentiment_score": float(item.get("sentiment_score", 50.0)),
                "reasoning": item.get("reasoning", ""),
                "engagement_context": item.get("engagement_context", ""),
                "raw_ai_json": item
            }

            try:
                supabase.table("tiktok_sentiment_analysis_results").upsert(
                    record, on_conflict="tiktok_post_id"
                ).execute()
                saved_count += 1
            except Exception as e:
                print(f"[SentimentService Error TikTok] Gagal simpan post_id {post_id}: {e}")

        return {
            "platform": "tiktok",
            "status": "success",
            "provider_used": provider,
            "batch_size_requested": batch_size,
            "unprocessed_remaining": len(unprocessed_rows) - saved_count,
            "analyzed_and_saved": saved_count
        }

    @classmethod
    async def analyze_all_unprocessed(cls, batch_size: int = 15) -> Dict[str, Any]:
        """Menganalisis sentimen seluruh platform (Instagram & TikTok)."""
        ig_res = await cls.analyze_unprocessed_instagram_captions(batch_size=batch_size)
        tt_res = await cls.analyze_unprocessed_tiktok_captions(batch_size=batch_size)

        return {
            "instagram": ig_res,
            "tiktok": tt_res
        }