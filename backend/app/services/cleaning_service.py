# backend/app/services/cleaning_service.py

from typing import Any, Dict
from app.core.database import supabase
from app.models.schemas import CaptionCleaner


class CleaningService:

    @classmethod
    async def process_uncleaned_instagram_captions(cls) -> Dict[str, Any]:
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

        # Ambil semua kolom (termasuk owner_username / username)
        query = supabase.table("instagram_posts").select("*")
        if existing_cleaned_ids:
            query = query.not_.in_("id", list(existing_cleaned_ids))

        uncleaned_posts = query.execute().data or []

        if not uncleaned_posts:
            return {
                "platform": "instagram",
                "status": "skipped",
                "message": "Semua caption di instagram_posts sudah selesai dibersihkan.",
                "total_uncleaned_found": 0,
                "successfully_cleaned": 0,
                "failed_count": 0,
            }

        processed_count = 0
        failed_count = 0

        for item in uncleaned_posts:
            post_id = item["id"]
            raw_caption = item.get("caption") or ""
            
            # Cek username Instagram
            username = (
                item.get("owner_username") 
                or item.get("username") 
                or ""
            ).lower()

            cleaned_data = CaptionCleaner.clean(raw_caption)

            # Validasi kata unmer di caption ATAU di username
            has_unmer = cleaned_data.has_unmer_keyword or ("unmer" in username)

            payload = {
                "instagram_post_id": post_id,
                "original_caption": cleaned_data.original_caption,
                "cleaned_caption": cleaned_data.cleaned_caption,
                "hashtags": cleaned_data.hashtags,
                "mentions": cleaned_data.mentions,
                "has_unmer_keyword": has_unmer,
                "caption_length": cleaned_data.caption_length,
                "word_count": cleaned_data.word_count,
            }

            try:
                supabase.table("cleaned_instagram_captions").upsert(
                    payload, on_conflict="instagram_post_id"
                ).execute()
                processed_count += 1
            except Exception as e:
                failed_count += 1
                print(
                    f"[CleaningService Error IG] Gagal memproses post_id {post_id}: {e}"
                )

        return {
            "platform": "instagram",
            "status": "success",
            "total_uncleaned_found": len(uncleaned_posts),
            "successfully_cleaned": processed_count,
            "failed_count": failed_count,
        }

    @classmethod
    async def process_uncleaned_tiktok_captions(cls) -> Dict[str, Any]:
        cleaned_res = (
            supabase.table("cleaned_tiktok_captions")
            .select("tiktok_post_id")
            .execute()
        )
        existing_cleaned_ids = {
            row["tiktok_post_id"]
            for row in (cleaned_res.data or [])
            if row.get("tiktok_post_id")
        }

        query = supabase.table("tiktok_posts").select("*")
        if existing_cleaned_ids:
            query = query.not_.in_("id", list(existing_cleaned_ids))

        uncleaned_posts = query.execute().data or []

        if not uncleaned_posts:
            return {
                "platform": "tiktok",
                "status": "skipped",
                "message": "Semua caption di tiktok_posts sudah selesai dibersihkan.",
                "total_uncleaned_found": 0,
                "successfully_cleaned": 0,
                "failed_count": 0,
            }

        processed_count = 0
        failed_count = 0

        for item in uncleaned_posts:
            post_id = item["id"]
            raw_caption = (
                item.get("caption")
                or item.get("desc")
                or item.get("description")
                or ""
            )

            # Cek username / nickname TikTok
            username = (
                item.get("owner_username")
                or item.get("owner_nickname")
                or item.get("username")
                or item.get("author_username")
                or ""
            ).lower()

            cleaned_data = CaptionCleaner.clean(raw_caption)

            # Validasi kata unmer di caption ATAU di username/nickname
            has_unmer = cleaned_data.has_unmer_keyword or ("unmer" in username)

            payload = {
                "tiktok_post_id": post_id,
                "original_caption": cleaned_data.original_caption,
                "cleaned_caption": cleaned_data.cleaned_caption,
                "hashtags": cleaned_data.hashtags,
                "mentions": cleaned_data.mentions,
                "has_unmer_keyword": has_unmer,
                "caption_length": cleaned_data.caption_length,
                "word_count": cleaned_data.word_count,
            }

            try:
                supabase.table("cleaned_tiktok_captions").upsert(
                    payload, on_conflict="tiktok_post_id"
                ).execute()
                processed_count += 1
            except Exception as e:
                failed_count += 1
                print(
                    f"[CleaningService Error TikTok] Gagal memproses post_id {post_id}: {e}"
                )

        return {
            "platform": "tiktok",
            "status": "success",
            "total_uncleaned_found": len(uncleaned_posts),
            "successfully_cleaned": processed_count,
            "failed_count": failed_count,
        }

    @classmethod
    async def process_all_uncleaned(cls) -> Dict[str, Any]:
        ig_result = await cls.process_uncleaned_instagram_captions()
        tt_result = await cls.process_uncleaned_tiktok_captions()

        return {"instagram": ig_result, "tiktok": tt_result}