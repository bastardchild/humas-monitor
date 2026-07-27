# backend/app/services/cleaning_service.py

from typing import Dict, Any
from app.core.database import supabase
from app.models.schemas import CaptionCleaner

class CleaningService:

    @classmethod
    async def process_uncleaned_captions(cls) -> Dict[str, Any]:
        # 1. Ambil daftar instagram_post_id yang SUDAH pernah di-clean
        cleaned_res = (
            supabase.table("cleaned_instagram_captions")
            .select("instagram_post_id")
            .execute()
        )
        existing_cleaned_ids = {
            row["instagram_post_id"] 
            for row in (cleaned_res.data or []) 
            if row.get("instagram_post_id")
        }

        # 2. Query record dari instagram_posts yang BELUM ADA di cleaned_instagram_captions
        query = supabase.table("instagram_posts").select("id, caption")
        if existing_cleaned_ids:
            query = query.not_.in_("id", list(existing_cleaned_ids))

        uncleaned_posts = query.execute().data or []

        if not uncleaned_posts:
            return {
                "status": "skipped",
                "message": "Semua caption di instagram_posts sudah selesai dibersihkan.",
                "processed_count": 0
            }

        processed_count = 0

        # 3. Proses setiap caption menggunakan model Pydantic
        for item in uncleaned_posts:
            post_id = item["id"]
            raw_caption = item.get("caption") or ""

            # Jalankan logika pembersihan Pydantic
            cleaned_data = CaptionCleaner.clean(raw_caption)

            payload = {
                "instagram_post_id": post_id,
                "original_caption": cleaned_data.original_caption,
                "cleaned_caption": cleaned_data.cleaned_caption,
                "hashtags": cleaned_data.hashtags,
                "mentions": cleaned_data.mentions,
                "has_unmer_keyword": cleaned_data.has_unmer_keyword,
                "caption_length": cleaned_data.caption_length,
                "word_count": cleaned_data.word_count
            }

            try:
                # Simpan ke tabel cleaned_instagram_captions
                supabase.table("cleaned_instagram_captions").upsert(
                    payload, on_conflict="instagram_post_id"
                ).execute()
                processed_count += 1
            except Exception as e:
                print(f"[CleaningService Error] Gagal memproses post_id {post_id}: {e}")

        return {
            "status": "success",
            "total_uncleaned_found": len(uncleaned_posts),
            "successfully_cleaned": processed_count
        }