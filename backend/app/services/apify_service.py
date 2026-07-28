# backend/app/services/apify_service.py

import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from apify_client import ApifyClient
from app.core.config import settings
from app.core.database import supabase


def extract_shortcode(url: str) -> Optional[str]:
    """
    Ekstrak Instagram Shortcode unik dari URL postingan/reel/tv.
    Contoh: 'https://www.instagram.com/p/C123xyz/?hl=id' -> 'C123xyz'
    """
    if not url:
        return None
    match = re.search(r"/(?:p|reel|tv)/([^/?#]+)", url)
    return match.group(1) if match else None


def extract_tiktok_video_id(url: str) -> Optional[str]:
    """
    Ekstrak ID Video unik dari URL TikTok.
    Contoh: 'https://www.tiktok.com/@username/video/7534061113365859586' -> '7534061113365859586'
    """
    if not url:
        return None
    match = re.search(r"/video/(\d+)", url)
    return match.group(1) if match else None


class ApifyService:

    @classmethod
    async def crawl_recent_instagram_posts(
        cls, 
        hours: int = 48, 
        min_score: float = 50.0
    ) -> Dict[str, Any]:
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # 1. Ambil raw_id dari scored_results yang memiliki relevance_score >= min_score (50)
        scored_res = (
            supabase.table("scored_results")
            .select("raw_id, relevance_score")
            .gte("relevance_score", min_score)
            .execute()
        )
        
        high_score_raw_ids = [
            row["raw_id"] for row in (scored_res.data or []) if row.get("raw_id")
        ]

        if not high_score_raw_ids:
            return {
                "status": "skipped",
                "message": f"Tidak ada data hasil scoring dengan relevance_score >= {min_score}.",
                "target_count": 0
            }

        # 2. Ambil raw_id dan short_code yang SUDAH pernah di-crawl di Supabase
        scraped_res = (
            supabase.table("instagram_posts")
            .select("raw_id, short_code")
            .execute()
        )
        
        scraped_raw_ids = {
            row["raw_id"] for row in (scraped_res.data or []) if row.get("raw_id")
        }
        scraped_shortcodes = {
            row["short_code"] for row in (scraped_res.data or []) if row.get("short_code")
        }

        # 3. Ambil raw_search_results tanpa .ilike agar Supabase/Cloudflare tidak error 500
        raw_res = (
            supabase.table("raw_search_results")
            .select("id, url, created_at")
            .in_("id", high_score_raw_ids)
            .gte("created_at", cutoff_time)
            .execute()
        )
        raw_items = raw_res.data or []

        if not raw_items:
            return {
                "status": "skipped",
                "message": f"Tidak ada data ber-skor >= {min_score} dalam {hours} jam terakhir.",
                "target_count": 0
            }

        targets: List[str] = []
        shortcode_to_raw_id: Dict[str, int] = {}
        url_to_raw_id: Dict[str, int] = {}

        # 4. Filter target khusus INSTAGRAM di Python
        for item in raw_items:
            raw_id = item["id"]
            url = item["url"]
            
            # Cek apakah ini URL Instagram & memiliki shortcode valid
            is_instagram = "instagram.com" in url.lower()
            shortcode = extract_shortcode(url)

            already_scraped = (raw_id in scraped_raw_ids) or (shortcode and shortcode in scraped_shortcodes)

            if is_instagram and shortcode and not already_scraped:
                targets.append(url)
                shortcode_to_raw_id[shortcode] = raw_id
                url_to_raw_id[url] = raw_id
                
                scraped_raw_ids.add(raw_id)
                scraped_shortcodes.add(shortcode)

        if not targets:
            return {
                "status": "skipped",
                "message": f"Semua postingan Instagram dengan skor >= {min_score} ({hours} jam terakhir) sudah di-crawl.",
                "target_count": 0
            }

        # 5. Trigger Apify Actor Instagram
        if not settings.APIFY_API_TOKEN:
            raise ValueError("APIFY_API_TOKEN belum dikonfigurasi di file .env")

        apify_client = ApifyClient(settings.APIFY_API_TOKEN)
        run_input = {
            "username": targets,
            "resultsLimit": 1
        }

        run = apify_client.actor(settings.APIFY_ACTOR_ID).call(run_input=run_input)

        # 6. Simpan hasil crawling ke Supabase
        dataset_items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        saved_count = 0

        for item in dataset_items:
            apify_shortcode = item.get("shortCode")
            input_url = item.get("inputUrl") or item.get("url") or ""

            raw_id = shortcode_to_raw_id.get(apify_shortcode) or url_to_raw_id.get(input_url)

            payload = {
                "raw_id": raw_id,
                "post_url": item.get("url") or input_url,
                "short_code": apify_shortcode,
                "owner_username": item.get("ownerUsername"),
                "caption": item.get("caption", ""),
                "likes_count": item.get("likesCount", 0),
                "comments_count": item.get("commentsCount", 0),
                "post_timestamp": item.get("timestamp"),
                "raw_apify_json": item
            }

            try:
                supabase.table("instagram_posts").upsert(payload, on_conflict="post_url").execute()
                saved_count += 1
            except Exception as e:
                print(f"[ApifyService Error] Gagal menyimpan Instagram URL {input_url}: {e}")

        return {
            "status": "success",
            "hours_window": hours,
            "min_score": min_score,
            "actor_id_used": settings.APIFY_ACTOR_ID,
            "total_target_urls": len(targets),
            "scraped_by_apify": len(dataset_items),
            "saved_to_supabase": saved_count
        }

    @classmethod
    async def crawl_recent_tiktok_posts(
        cls, 
        hours: int = 48, 
        min_score: float = 50.0
    ) -> Dict[str, Any]:
        """
        Crawl detail video TikTok menggunakan Actor clockworks/tiktok-scraper.
        """
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # 1. Ambil raw_id dari scored_results
        scored_res = (
            supabase.table("scored_results")
            .select("raw_id, relevance_score")
            .gte("relevance_score", min_score)
            .execute()
        )
        
        high_score_raw_ids = [
            row["raw_id"] for row in (scored_res.data or []) if row.get("raw_id")
        ]

        if not high_score_raw_ids:
            return {
                "status": "skipped",
                "message": f"Tidak ada data hasil scoring dengan relevance_score >= {min_score}.",
                "target_count": 0
            }

        # 2. Ambil raw_id & video_id yang SUDAH pernah di-crawl di tabel tiktok_posts
        scraped_res = (
            supabase.table("tiktok_posts")
            .select("raw_id, video_id")
            .execute()
        )
        
        scraped_raw_ids = {
            row["raw_id"] for row in (scraped_res.data or []) if row.get("raw_id")
        }
        scraped_video_ids = {
            row["video_id"] for row in (scraped_res.data or []) if row.get("video_id")
        }

        # 3. Ambil raw_search_results tanpa .ilike
        raw_res = (
            supabase.table("raw_search_results")
            .select("id, url, created_at")
            .in_("id", high_score_raw_ids)
            .gte("created_at", cutoff_time)
            .execute()
        )
        raw_items = raw_res.data or []

        if not raw_items:
            return {
                "status": "skipped",
                "message": f"Tidak ada data ber-skor >= {min_score} dalam {hours} jam terakhir.",
                "target_count": 0
            }

        targets: List[str] = []
        video_id_to_raw_id: Dict[str, int] = {}
        url_to_raw_id: Dict[str, int] = {}

        # 4. Filter target khusus TIKTOK di Python
        for item in raw_items:
            raw_id = item["id"]
            url = item["url"]
            
            # Cek apakah ini URL TikTok & memiliki video ID valid
            is_tiktok = "tiktok.com" in url.lower()
            video_id = extract_tiktok_video_id(url)

            already_scraped = (raw_id in scraped_raw_ids) or (video_id and video_id in scraped_video_ids)

            if is_tiktok and video_id and not already_scraped:
                targets.append(url)
                if video_id:
                    video_id_to_raw_id[video_id] = raw_id
                url_to_raw_id[url] = raw_id
                
                scraped_raw_ids.add(raw_id)
                if video_id:
                    scraped_video_ids.add(video_id)

        if not targets:
            return {
                "status": "skipped",
                "message": f"Semua postingan TikTok dengan skor >= {min_score} ({hours} jam terakhir) sudah di-crawl.",
                "target_count": 0
            }

        # 5. Trigger Actor TikTok Scraper
        if not settings.APIFY_API_TOKEN:
            raise ValueError("APIFY_API_TOKEN belum dikonfigurasi di file .env")

        actor_id = getattr(settings, "APIFY_TIKTOK_ACTOR_ID", "clockworks/tiktok-scraper")
        apify_client = ApifyClient(settings.APIFY_API_TOKEN)

        run_input = {
            "postURLs": targets,
            "resultsPerPage": len(targets)
        }

        run = apify_client.actor(actor_id).call(run_input=run_input)

        # 6. Simpan hasil crawling ke Supabase
        dataset_items = list(apify_client.dataset(run["defaultDatasetId"]).iterate_items())
        saved_count = 0

        for item in dataset_items:
            apify_video_id = str(item.get("id") or "")
            web_video_url = item.get("webVideoUrl") or ""
            
            raw_id = video_id_to_raw_id.get(apify_video_id) or url_to_raw_id.get(web_video_url)

            author_meta = item.get("authorMeta") or {}
            video_meta = item.get("videoMeta") or {}
            music_meta = item.get("musicMeta") or {}

            payload = {
                "raw_id": raw_id,
                "post_url": web_video_url or item.get("url"),
                "video_id": apify_video_id,
                "owner_username": author_meta.get("name"),
                "owner_nickname": author_meta.get("nickName"),
                "caption": item.get("text", ""),
                "likes_count": item.get("diggCount", 0),
                "comments_count": item.get("commentCount", 0),
                "shares_count": item.get("shareCount", 0),
                "plays_count": item.get("playCount", 0),
                "collect_count": item.get("collectCount", 0),
                "video_duration": video_meta.get("duration", 0),
                "music_title": music_meta.get("musicName"),
                "music_author": music_meta.get("musicAuthor"),
                "post_timestamp": item.get("createTimeISO"),
                "raw_apify_json": item
            }

            try:
                supabase.table("tiktok_posts").upsert(payload, on_conflict="post_url").execute()
                saved_count += 1
            except Exception as e:
                print(f"[ApifyService Error] Gagal menyimpan TikTok URL {web_video_url}: {e}")

        return {
            "status": "success",
            "hours_window": hours,
            "min_score": min_score,
            "actor_id_used": actor_id,
            "total_target_urls": len(targets),
            "scraped_by_apify": len(dataset_items),
            "saved_to_supabase": saved_count
        }