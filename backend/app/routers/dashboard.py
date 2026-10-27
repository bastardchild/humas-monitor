import json
import math
import csv
import io
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Request, Query, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from app.core.db import get_db
import httpx

router = APIRouter(tags=["Dashboard UI"])
templates = Jinja2Templates(directory="app/templates")

WIB = timezone(timedelta(hours=7))

def parse_dt(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        try:
            dt = datetime.strptime(dt_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return None

def format_wib(dt: Optional[datetime], fmt: str = "%d %b %Y, %H:%M WIB") -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt_wib = dt.astimezone(WIB)
    return dt_wib.strftime(fmt)

def fetch_all_dashboard_data():
    flattened = []
    with get_db() as db:
        # 1. Instagram
        try:
            sql_ig = """
                SELECT 
                    sar.post_url, sar.sentiment, sar.sentiment_score, sar.reasoning, sar.created_at as analyzed_at,
                    ip.owner_username, ip.likes_count, ip.comments_count, ip.post_timestamp,
                    cic.cleaned_caption, cic.hashtags
                FROM sentiment_analysis_results sar
                LEFT JOIN instagram_posts ip ON sar.post_url = ip.post_url
                LEFT JOIN cleaned_instagram_captions cic ON sar.post_url = cic.post_url
            """
            ig_rows = [dict(r) for r in db.execute(sql_ig).fetchall()]
            for r in ig_rows:
                score_val = float(r.get("sentiment_score", 50.0))
                if score_val > 1.0:
                    score_val = score_val / 100.0
                ts = parse_dt(r.get("post_timestamp")) or parse_dt(r.get("analyzed_at")) or datetime.now(timezone.utc)
                flattened.append({
                    "id": f"ig_{r.get('post_url','')}",
                    "platform": "Instagram",
                    "sentiment": (r.get("sentiment") or "neutral").lower(),
                    "sentiment_score": score_val,
                    "reasoning": r.get("reasoning","") or "Tidak ada reasoning",
                    "engagement_context": f"{r.get('likes_count',0) or 0} likes, {r.get('comments_count',0) or 0} komentar",
                    "analyzed_at": parse_dt(r.get("analyzed_at")),
                    "post_url": r.get("post_url") or "#",
                    "username": r.get("owner_username") or "Unknown",
                    "likes": r.get("likes_count", 0) or 0,
                    "comments": r.get("comments_count", 0) or 0,
                    "views": 0,
                    "rating": None,
                    "post_timestamp": ts,
                    "post_timestamp_str": format_wib(ts),
                    "caption": r.get("cleaned_caption") or r.get("reasoning") or "",
                })
        except Exception as e:
            print("Dashboard IG fetch error:", e)

        # 2. TikTok
        try:
            sql_tt = """
                SELECT 
                    tsar.post_url, tsar.sentiment, tsar.sentiment_score, tsar.reasoning, tsar.created_at as analyzed_at,
                    tp.owner_username, tp.likes_count, tp.comments_count, tp.post_timestamp,
                    ctc.cleaned_caption, ctc.hashtags
                FROM tiktok_sentiment_analysis_results tsar
                LEFT JOIN tiktok_posts tp ON tsar.post_url = tp.post_url
                LEFT JOIN cleaned_tiktok_captions ctc ON tsar.post_url = ctc.post_url
            """
            tt_rows = [dict(r) for r in db.execute(sql_tt).fetchall()]
            for r in tt_rows:
                score_val = float(r.get("sentiment_score", 50.0))
                if score_val > 1.0:
                    score_val = score_val / 100.0
                ts = parse_dt(r.get("post_timestamp")) or parse_dt(r.get("analyzed_at")) or datetime.now(timezone.utc)
                username = (r.get("owner_username") or "Unknown").strip().lstrip("@")
                flattened.append({
                    "id": f"tt_{r.get('post_url','')}",
                    "platform": "TikTok",
                    "sentiment": (r.get("sentiment") or "neutral").lower(),
                    "sentiment_score": score_val,
                    "reasoning": r.get("reasoning","") or "Tidak ada reasoning",
                    "engagement_context": f"{r.get('likes_count',0) or 0} likes, {r.get('comments_count',0) or 0} komentar",
                    "analyzed_at": parse_dt(r.get("analyzed_at")),
                    "post_url": r.get("post_url") or "#",
                    "username": username or "Unknown",
                    "likes": r.get("likes_count", 0) or 0,
                    "comments": r.get("comments_count", 0) or 0,
                    "views": 0,
                    "rating": None,
                    "post_timestamp": ts,
                    "post_timestamp_str": format_wib(ts),
                    "caption": r.get("cleaned_caption") or r.get("reasoning") or "",
                })
        except Exception as e:
            print("Dashboard TikTok fetch error:", e)

        # 3. Google Reviews
        try:
            sql_gr = "SELECT * FROM raw_google_reviews ORDER BY id DESC LIMIT 100"
            gr_rows = [dict(r) for r in db.execute(sql_gr).fetchall()]
            for r in gr_rows:
                try:
                    j = json.loads(r.get("review_json") or "{}") if isinstance(r.get("review_json"), str) else (r.get("review_json") or {})
                except Exception:
                    j = {}
                rating = j.get("rating")
                if rating is None and "rating" in r:
                    rating = r.get("rating")
                
                if rating is not None:
                    rating = int(rating)
                    if rating >= 4:
                        sentiment = "positive"
                    elif rating == 3:
                        sentiment = "neutral"
                    else:
                        sentiment = "negative"
                else:
                    sentiment = "neutral"
                    rating = 0

                ts = parse_dt(r.get("created_at")) or datetime.now(timezone.utc)
                author = j.get("author_name") or r.get("author_name") or "Anonymous User"
                snippet = j.get("snippet") or r.get("snippet") or ""

                flattened.append({
                    "id": f"gr_{r['id']}",
                    "platform": "Google Review",
                    "sentiment": sentiment,
                    "sentiment_score": (rating * 0.2) if rating else 0.5,
                    "reasoning": f"Berdasarkan ulasan bintang {rating} di Google Maps.",
                    "engagement_context": f"Google Maps Rating: {rating} / 5",
                    "analyzed_at": ts,
                    "post_url": f"https://www.google.com/maps/place/?q=place_id:{r.get('place_id', '')}",
                    "username": author,
                    "likes": 0,
                    "comments": 0,
                    "views": 0,
                    "rating": rating,
                    "post_timestamp": ts,
                    "post_timestamp_str": format_wib(ts),
                    "caption": snippet,
                })
        except Exception as e:
            print("Dashboard Google Reviews fetch error:", e)

    # Sort descending by timestamp
    flattened.sort(key=lambda x: x["post_timestamp"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return flattened

@router.get("/", response_class=HTMLResponse)
async def render_dashboard_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@router.get("/partials/dashboard-content", response_class=HTMLResponse)
async def get_dashboard_content(
    request: Request,
    platforms: Optional[List[str]] = Query(default=None),
    date_range: str = Query("Last 7 Days"),
    sentiments: Optional[List[str]] = Query(default=None),
    query: str = Query(""),
    social_page: int = Query(1, ge=1),
    review_page: int = Query(1, ge=1)
):
    all_raw_data = fetch_all_dashboard_data()

    # Filter Platforms
    filtered_data = all_raw_data
    if platforms:
        filtered_data = [item for item in filtered_data if item["platform"] in platforms]
    
    # Filter Date Range
    now = datetime.now(timezone.utc)
    cutoff = None
    if date_range == "Last 24 Hours":
        cutoff = now - timedelta(hours=24)
    elif date_range == "Last 3 Days":
        cutoff = now - timedelta(days=3)
    elif date_range == "Last 7 Days":
        cutoff = now - timedelta(days=7)
    elif date_range == "Last 30 Days":
        cutoff = now - timedelta(days=30)
    elif date_range == "Last 90 Days":
        cutoff = now - timedelta(days=90)
    
    if cutoff:
        filtered_data = [item for item in filtered_data if item["post_timestamp"] and item["post_timestamp"] >= cutoff]

    # Filter Sentiments
    if sentiments:
        filtered_data = [item for item in filtered_data if item["sentiment"] in sentiments]

    # Filter Query
    if query.strip():
        q_lower = query.strip().lower()
        filtered_data = [
            item for item in filtered_data 
            if q_lower in item.get("caption", "").lower() or q_lower in item.get("username", "").lower()
        ]

    # KPI Metrics Calculation
    total_posts = len(filtered_data)
    total_likes = sum(item["likes"] for item in filtered_data)
    total_comments = sum(item["comments"] for item in filtered_data)
    pos_count = sum(1 for item in filtered_data if item["sentiment"] == "positive")
    pos_ratio = (pos_count / total_posts * 100.0) if total_posts > 0 else 0.0

    last_updated_str = "-"
    if all_raw_data:
        max_dt = max((item.get("analyzed_at") for item in all_raw_data if item.get("analyzed_at")), default=None)
        if not max_dt:
            max_dt = max((item.get("post_timestamp") for item in all_raw_data if item.get("post_timestamp")), default=None)
        if max_dt:
            last_updated_str = format_wib(max_dt, "%d %b %Y, %H:%M:%S WIB")

    # Chart Data Preparation
    # 1. Pie Chart
    sent_counts = {
        "positive": sum(1 for item in filtered_data if item["sentiment"] == "positive"),
        "neutral": sum(1 for item in filtered_data if item["sentiment"] == "neutral"),
        "negative": sum(1 for item in filtered_data if item["sentiment"] == "negative")
    }
    pie_chart_data = {
        "labels": ["Positive", "Neutral", "Negative"],
        "data": [sent_counts["positive"], sent_counts["neutral"], sent_counts["negative"]]
    }

    # 2. Trend Line Chart
    trend_by_date = {}
    for item in filtered_data:
        d_str = format_wib(item["post_timestamp"], "%Y-%m-%d") if item["post_timestamp"] else "Unknown"
        if d_str not in trend_by_date:
            trend_by_date[d_str] = {"positive": 0, "neutral": 0, "negative": 0}
        s = item["sentiment"] if item["sentiment"] in ["positive", "neutral", "negative"] else "neutral"
        trend_by_date[d_str][s] += 1

    sorted_dates = sorted(trend_by_date.keys())
    trend_chart_data = {
        "dates": sorted_dates,
        "positive": [trend_by_date[d]["positive"] for d in sorted_dates],
        "neutral": [trend_by_date[d]["neutral"] for d in sorted_dates],
        "negative": [trend_by_date[d]["negative"] for d in sorted_dates]
    }

    # 3. Platform Comparison Chart
    plat_labels = ["Instagram", "TikTok", "Google Review"]
    plat_data = {
        "positive": [sum(1 for i in filtered_data if i["platform"] == p and i["sentiment"] == "positive") for p in plat_labels],
        "neutral": [sum(1 for i in filtered_data if i["platform"] == p and i["sentiment"] == "neutral") for p in plat_labels],
        "negative": [sum(1 for i in filtered_data if i["platform"] == p and i["sentiment"] == "negative") for p in plat_labels]
    }
    platform_chart_data = {
        "labels": plat_labels,
        "positive": plat_data["positive"],
        "neutral": plat_data["neutral"],
        "negative": plat_data["negative"]
    }

    # 4. Engagement Chart (Instagram vs TikTok)
    eng_labels = ["Instagram", "TikTok"]
    eng_likes = []
    eng_comments = []
    for p in eng_labels:
        items_p = [i for i in filtered_data if i["platform"] == p]
        count_p = len(items_p)
        avg_likes = sum(i["likes"] for i in items_p) / count_p if count_p > 0 else 0
        avg_comments = sum(i["comments"] for i in items_p) / count_p if count_p > 0 else 0
        eng_likes.append(round(avg_likes, 1))
        eng_comments.append(round(avg_comments, 1))

    engagement_chart_data = {
        "labels": eng_labels,
        "likes": eng_likes,
        "comments": eng_comments
    }

    chart_json = json.dumps({
        "pie": pie_chart_data,
        "trend": trend_chart_data,
        "platform": platform_chart_data,
        "engagement": engagement_chart_data
    })

    # Pagination for Social Feed (Instagram & TikTok)
    social_posts = [item for item in filtered_data if item["platform"] in ["Instagram", "TikTok"]]
    social_per_page = 10
    social_total_pages = max(1, math.ceil(len(social_posts) / social_per_page))
    if social_page > social_total_pages:
        social_page = 1
    social_start = (social_page - 1) * social_per_page
    social_page_items = social_posts[social_start:social_start + social_per_page]

    # Pagination for Google Reviews
    review_posts = [item for item in filtered_data if item["platform"] == "Google Review"]
    review_per_page = 10
    review_total_pages = max(1, math.ceil(len(review_posts) / review_per_page))
    if review_page > review_total_pages:
        review_page = 1
    review_start = (review_page - 1) * review_per_page
    review_page_items = review_posts[review_start:review_start + review_per_page]

    return templates.TemplateResponse(
        "partials/dashboard_content.html",
        {
            "request": request,
            "total_posts": total_posts,
            "total_likes": total_likes,
            "total_comments": total_comments,
            "pos_ratio": pos_ratio,
            "last_updated_str": last_updated_str,
            "chart_json": chart_json,
            "social_posts": social_posts,
            "social_page": social_page,
            "social_total_pages": social_total_pages,
            "social_page_items": social_page_items,
            "review_posts": review_posts,
            "review_page": review_page,
            "review_total_pages": review_total_pages,
            "review_page_items": review_page_items,
            "all_items": filtered_data
        }
    )

@router.post("/partials/pipeline/run", response_class=HTMLResponse)
async def run_pipeline(request: Request):
    pipeline_steps = [
        {"name": "1. Search Fetch Social", "url": "http://127.0.0.1:8000/api/v1/search/fetch/social"},
        {"name": "1.1 Search Fetch Reviews", "url": "http://127.0.0.1:8000/api/v1/search/fetch/reviews"},
        {"name": "1.2 Search Fetch News", "url": "http://127.0.0.1:8000/api/v1/search/fetch/news"},
        {"name": "2. Scoring Process Social", "url": "http://127.0.0.1:8000/api/v1/score/process/social"},
        {"name": "3. Instagram Crawler", "url": "http://127.0.0.1:8000/api/v1/crawl/instagram"},
        {"name": "4. Tiktok Crawler", "url": "http://127.0.0.1:8000/api/v1/crawl/tiktok"},
        {"name": "5. Data Cleaning Instagram", "url": "http://127.0.0.1:8000/api/v1/clean/instagram"},
        {"name": "6. Data Cleaning Tiktok", "url": "http://127.0.0.1:8000/api/v1/clean/tiktok"},
        {"name": "7. Sentiment Analysis Instagram", "url": "http://127.0.0.1:8000/api/v1/sentiment/instagram"},
        {"name": "8. Sentiment Analysis Tiktok", "url": "http://127.0.0.1:8000/api/v1/sentiment/tiktok"},
    ]

    pipeline_result = {"success": True, "error": None}
    async with httpx.AsyncClient(timeout=300.0) as client:
        for step in pipeline_steps:
            try:
                res = await client.post(step["url"])
                if res.status_code not in [200, 201]:
                    pipeline_result = {
                        "success": False,
                        "error": f"Langkah '{step['name']}' gagal dengan status HTTP {res.status_code}: {res.text}"
                    }
                    break
            except Exception as e:
                pipeline_result = {
                    "success": False,
                    "error": f"Error koneksi pada '{step['name']}': {str(e)}"
                }
                break

    return templates.TemplateResponse(
        "partials/pipeline_status.html",
        {"request": request, "pipeline_result": pipeline_result}
    )

@router.get("/export/csv")
async def export_csv():
    data = fetch_all_dashboard_data()
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "ID", "Platform", "Username", "Sentiment", "Sentiment Score", 
        "Rating", "Likes", "Comments", "Caption", "Reasoning", 
        "Engagement Context", "Post URL", "Post Timestamp"
    ])
    
    for row in data:
        writer.writerow([
            row.get("id"),
            row.get("platform"),
            row.get("username"),
            row.get("sentiment"),
            f"{row.get('sentiment_score', 0):.2f}",
            row.get("rating") if row.get("rating") is not None else "",
            row.get("likes", 0),
            row.get("comments", 0),
            row.get("caption", ""),
            row.get("reasoning", ""),
            row.get("engagement_context", ""),
            row.get("post_url", ""),
            row.get("post_timestamp_str", "")
        ])

    output.seek(0)
    filename = f"unmer_sentiment_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
