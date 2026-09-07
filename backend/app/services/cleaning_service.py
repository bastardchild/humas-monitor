# backend/app/services/cleaning_service.py
from typing import Any, Dict
from app.core.db import get_db
import json
from app.models.schemas import CaptionCleaner

class CleaningService:
    @classmethod
    async def process_uncleaned_instagram_captions(cls) -> Dict[str, Any]:
        with get_db() as db:
            existing = {r[0] for r in db.execute("SELECT post_url FROM cleaned_instagram_captions").fetchall()}
            if existing:
                ph = ",".join("?"*len(existing))
                rows = db.execute(f"SELECT * FROM instagram_posts WHERE post_url NOT IN ({ph})", tuple(existing)).fetchall()
            else:
                rows = db.execute("SELECT * FROM instagram_posts").fetchall()
            uncleaned = [dict(r) for r in rows]
        if not uncleaned:
            return {"platform":"instagram","status":"skipped","message":"Semua caption sudah dibersihkan.","total_uncleaned_found":0,"successfully_cleaned":0,"failed_count":0}
        cnt=fail=0
        for item in uncleaned:
            raw_caption = item.get("caption") or item.get("raw_json","") or ""
            if isinstance(raw_caption, str) and raw_caption.startswith("{"):
                try: raw_caption=json.loads(raw_caption).get("caption","")
                except: pass
            username=(item.get("owner_username") or item.get("username") or "").lower()
            cleaned=CaptionCleaner.clean(raw_caption)
            has_unmer=cleaned.has_unmer_keyword or ("unmer" in username)
            try:
                with get_db() as db:
                    db.execute("INSERT OR REPLACE INTO cleaned_instagram_captions (post_url,cleaned_caption,hashtags,mentions,has_unmer_keyword) VALUES (?,?,?,?,?)",
                               (item.get("post_url",""), cleaned.cleaned_caption, json.dumps(cleaned.hashtags), json.dumps(cleaned.mentions), int(has_unmer)))
                cnt+=1
            except Exception as e:
                fail+=1; print(f"[Cleaning IG] {e}")
        return {"platform":"instagram","status":"success","total_uncleaned_found":len(uncleaned),"successfully_cleaned":cnt,"failed_count":fail}

    @classmethod
    async def process_uncleaned_tiktok_captions(cls) -> Dict[str, Any]:
        with get_db() as db:
            existing = {r[0] for r in db.execute("SELECT post_url FROM cleaned_tiktok_captions").fetchall()}
            if existing:
                ph=",".join("?"*len(existing))
                rows=db.execute(f"SELECT * FROM tiktok_posts WHERE post_url NOT IN ({ph})", tuple(existing)).fetchall()
            else:
                rows=db.execute("SELECT * FROM tiktok_posts").fetchall()
            uncleaned=[dict(r) for r in rows]
        if not uncleaned:
            return {"platform":"tiktok","status":"skipped","message":"Semua caption TikTok sudah dibersihkan.","total_uncleaned_found":0,"successfully_cleaned":0,"failed_count":0}
        cnt=fail=0
        for item in uncleaned:
            raw_caption=item.get("caption") or item.get("desc") or item.get("description") or ""
            username=(item.get("owner_username") or item.get("owner_nickname") or item.get("username") or "").lower()
            cleaned=CaptionCleaner.clean(raw_caption)
            has_unmer=cleaned.has_unmer_keyword or ("unmer" in username)
            try:
                with get_db() as db:
                    db.execute("INSERT OR REPLACE INTO cleaned_tiktok_captions (post_url,cleaned_caption,hashtags,mentions,has_unmer_keyword) VALUES (?,?,?,?,?)",
                               (item.get("post_url",""), cleaned.cleaned_caption, json.dumps(cleaned.hashtags), json.dumps(cleaned.mentions), int(has_unmer)))
                cnt+=1
            except Exception as e:
                fail+=1; print(f"[Cleaning TikTok] {e}")
        return {"platform":"tiktok","status":"success","total_uncleaned_found":len(uncleaned),"successfully_cleaned":cnt,"failed_count":fail}

    @classmethod
    async def process_all_uncleaned(cls) -> Dict[str, Any]:
        return {"instagram": await cls.process_uncleaned_instagram_captions(), "tiktok": await cls.process_uncleaned_tiktok_captions()}
