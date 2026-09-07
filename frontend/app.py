import os
import requests
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import json
import httpx  # frontend reads via backend API (SQLite)


# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="UNMER Monitor - Cross-Platform Sentiment Dashboard",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# 1.5. AUTHENTICATION CHECK & EMAIL WHITELIST (GOOGLE SSO)
# -----------------------------------------------------------------------------
# 1. Cek Apakah User Sudah Login via Google
if not st.user.is_logged_in:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.image("https://unmer.ac.id/wp-content/uploads/2020/07/Branding_Putih-300x118.png", width=180)
        st.title(":material/lock: UNMER Monitor")
        st.subheader("Cross-Platform Sentiment Dashboard")
        st.write("Silakan login menggunakan akun Google Anda untuk mengakses dashboard internal.")
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button(":material/vpn_key: Login dengan Google", type="primary", use_container_width=True):
            st.login()
            
    st.stop()

# 2. Cek Whitelist Email dari File .env
allowed_emails_env = os.getenv("ALLOWED_EMAILS", "")
ALLOWED_EMAILS = [email.strip().lower() for email in allowed_emails_env.split(",") if email.strip()]

user_email = getattr(st.user, "email", "").lower()

if ALLOWED_EMAILS and user_email not in ALLOWED_EMAILS:
    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.error(f":material/block: **Akses Ditolak!**\n\nEmail `{user_email}` tidak terdaftar untuk mengakses dashboard ini.")
        st.caption("Silakan hubungi administrator jika Anda memerlukan akses.")
        
        if st.button(":material/logout: Keluar / Ganti Akun", type="primary", use_container_width=True):
            st.logout()
            
    st.stop()

# Custom CSS untuk UI Modern & Card Metrics
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300,0,0" rel="stylesheet" />
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Share+Tech+Mono&display=swap');
    .ms { font-family: 'Material Symbols Outlined'; font-weight: 300; font-style: normal; font-size: 18px; line-height: 1; vertical-align: middle; }
    .stApp { background: #0a0f14; color: #e6f0e8; font-family: 'JetBrains Mono', monospace; font-size: 16px; line-height: 1.6; }
    h1 { font-family: 'Share Tech Mono', monospace; font-size: 28px; color: #b8ffcc !important; letter-spacing: 0.04em; text-transform: uppercase; }
    h2 { font-family: 'Share Tech Mono', monospace; font-size: 22px; color: #d0ffe0 !important; }
    h3 { font-family: 'JetBrains Mono', monospace; font-size: 18px; color: #e6f0e8 !important; font-weight: 600; }
    p, span, div, label { font-family: 'JetBrains Mono', monospace; font-size: 15px; color: #e6f0e8; }
    small, .caption { font-size: 13px; color: #a8c0b0; }
    .metric-card { background: #111e16; padding: 16px 18px; border-radius: 10px; border: 1px solid rgba(168,255,200,0.22); text-align: center; }
    .metric-value { font-family: 'Share Tech Mono', monospace; font-size: 30px; color: #7affa8; }
    .metric-label { font-size: 13px; color: #b0c8b8; letter-spacing: 0.08em; text-transform: uppercase; }
    .badge-positive { background: #0d2a18; color: #e6fff0; border: 1px solid #1a6b3a; padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: 600; }
    .badge-neutral { background: #2a260d; color: #fff8cc; border: 1px solid #8a7a1a; padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: 600; }
    .badge-negative { background: #2a1218; color: #ffe6eb; border: 1px solid #8a2a3a; padding: 4px 10px; border-radius: 4px; font-size: 13px; font-weight: 600; }
    .badge-instagram { background: #0d1e2a; color: #d0eaff; border: 1px solid #2a5a7a; font-size: 12px; }
    .badge-tiktok { background: #0d1e16; color: #d0ffe8; border: 1px solid #2a6b4a; font-size: 12px; }
    .badge-google-review { background: #1a1e2a; color: #e0e8ff; border: 1px solid #3a4a6a; font-size: 12px; }
    .post-card { background: #111e16; border: 1px solid rgba(168,200,180,0.18); border-radius: 8px; padding: 16px; margin-bottom: 12px; color: #e6f0e8; }
    .post-card p { color: #e6f0e8 !important; font-size: 15px; line-height: 1.6; }
    section[data-testid="stSidebar"] { background: #0d1410; border-right: 1px solid rgba(168,255,200,0.14); }
    section[data-testid="stSidebar"] * { color: #e6f0e8; }
    .stButton>button { background: #143320; color: #e6fff0; font-family: 'JetBrains Mono', monospace; font-size: 15px; font-weight: 600; border: 1px solid #2a6b3a; min-height: 40px; }
    .stButton>button:hover { background: #1a4028; border-color: #3a8a4a; }
    a { color: #7affa8; text-decoration: underline; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. BACKEND CONNECTION (SQLite via API)
# -----------------------------------------------------------------------------
load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000/api/v1").rstrip("/")

# COLOR PALETTE
COLOR_MAP = {
    "positive": "#10b981",  # Emerald Green
    "neutral": "#f59e0b",   # Amber
    "negative": "#ef4444"   # Red
}

# -----------------------------------------------------------------------------
# 3. DATA FETCHING (INSTAGRAM, TIKTOK, & GOOGLE REVIEWS)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_sentiment_data() -> pd.DataFrame:
    """Mengambil dan menggabungkan data hasil analisis dari Instagram, TikTok, & Google Reviews."""
    flattened = []

    # --- 1. FETCH INSTAGRAM (via backend SQLite) ---
    try:
        try:
            j=httpx.get(f"{BACKEND_URL}/sentiment/results?limit=1000", timeout=15).json()
            d=j.get("data",{})
            ig_res=d.get("instagram",[]) if isinstance(d,dict) else []
        except Exception:
            ig_res=[]
        for r in (ig_res if isinstance(ig_res, list) else []):
            flattened.append({
                "id": f"ig_{r.get('post_url','')}",
                "platform": "Instagram",
                "sentiment": (r.get("sentiment") or "neutral").lower(),
                "sentiment_score": float(r.get("sentiment_score", 50))/100 if r.get("sentiment_score",50)>1 else float(r.get("sentiment_score",0.5)),
                "reasoning": r.get("reasoning","") or "Tidak ada reasoning",
                "engagement_context": r.get("engagement_context","") or f"{r.get('likes_count',0)} likes",
                "analyzed_at": pd.to_datetime(r.get("analyzed_at") or r.get("created_at")),
                "post_url": r.get("ig_url") or r.get("post_url") or "#",
                "username": r.get("owner_username") or "Unknown",
                "likes": r.get("likes_count",0),
                "comments": r.get("comments_count",0),
                "views": 0,
                "rating": None,
                "total_engagement": (r.get("likes_count",0) or 0)+(r.get("comments_count",0) or 0),
                "post_timestamp": pd.to_datetime(r.get("post_timestamp")) if r.get("post_timestamp") else pd.to_datetime(r.get("analyzed_at") or r.get("created_at")),
                "caption": r.get("cleaned_caption","") or "",
                "hashtags": json.loads(r["hashtags"]) if isinstance(r.get("hashtags"), str) and r.get("hashtags") else (r.get("hashtags") or [])
            })
    except Exception as e:
        st.warning(f"Gagal mengambil data Instagram: {e}")

    # --- 2. FETCH TIKTOK (via backend SQLite) ---
    try:
        try:
            if 'd' not in locals():
                j=httpx.get(f"{BACKEND_URL}/sentiment/results?limit=1000", timeout=15).json()
                d=j.get("data",{})
            tt_res=d.get("tiktok",[]) if isinstance(d,dict) else []
        except Exception:
            tt_res=[]
        for r in (tt_res if isinstance(tt_res,list) else []):

            raw_username=(r.get("owner_username") or "Unknown").strip().lstrip("@")
            flattened.append({
                "id": f"tt_{r.get('post_url','')}",
                "platform": "TikTok",
                "sentiment": (r.get("sentiment") or "neutral").lower(),
                "sentiment_score": float(r.get("sentiment_score",50))/100 if r.get("sentiment_score",50)>1 else float(r.get("sentiment_score",0.5)),
                "reasoning": r.get("reasoning","") or "Tidak ada reasoning",
                "engagement_context": r.get("engagement_context","") or "",
                "analyzed_at": pd.to_datetime(r.get("analyzed_at") or r.get("created_at")),
                "post_url": r.get("tt_url") or r.get("post_url") or "#",
                "username": raw_username or "Unknown",
                "likes": r.get("likes_count",0),
                "comments": r.get("comments_count",0),
                "views": 0,
                "rating": None,
                "total_engagement": (r.get("likes_count",0) or 0)+(r.get("comments_count",0) or 0),
                "post_timestamp": pd.to_datetime(r.get("post_timestamp")) if r.get("post_timestamp") else pd.to_datetime(r.get("analyzed_at") or r.get("created_at")),
                "caption": r.get("cleaned_caption","") or "",
                "hashtags": json.loads(r["hashtags"]) if isinstance(r.get("hashtags"),str) and r.get("hashtags") else (r.get("hashtags") or [])
            })
    except Exception as e:
        st.warning(f"Gagal mengambil data TikTok: {e}")

    # --- 3. FETCH GOOGLE REVIEWS (via backend SQLite) ---
    try:
        try:
            gr_res = httpx.get(f"{BACKEND_URL}/search/reviews?limit=100", timeout=10).json().get("data", [])
        except Exception:
            gr_res=[]
        for r in (gr_res if isinstance(gr_res, list) else []):
            rating = r.get("rating")
            # Konversi rating bintang ke sentimen secara otomatis jika diperlukan
            if rating is not None:
                if rating >= 4:
                    sentiment = "positive"
                elif rating == 3:
                    sentiment = "neutral"
                else:
                    sentiment = "negative"
            else:
                sentiment = "neutral"

            created_at = pd.to_datetime(r.get("created_at"))

            flattened.append({
                "id": f"gr_{r['id']}",
                "platform": "Google Review",
                "sentiment": sentiment,
                # "sentiment_score": (rating / 5.0) if rating else 0.5,
                "sentiment_score": (rating * 20) if rating else 50.0,
                "reasoning": f"Berdasarkan ulasan bintang {rating} di Google Maps.",
                "engagement_context": f"Google Maps Rating: {rating} / 5",
                "analyzed_at": created_at,
                "post_url": f"https://www.google.com/maps/place/?q=place_id:{r.get('review_id', '')}",
                "username": r.get("author_name") or "Anonymous User",
                "likes": 0,
                "comments": 0,
                "views": 0,
                "rating": rating,
                "total_engagement": 0,
                "post_timestamp": created_at,
                "caption": r.get("snippet", ""),
                "hashtags": []
            })
    except Exception as e:
        st.warning(f"Gagal mengambil data Google Reviews: {e}")

    df = pd.DataFrame(flattened)
    if not df.empty and "post_timestamp" in df.columns:
        df = df.sort_values(by="post_timestamp", ascending=False)
    return df

df_raw = fetch_sentiment_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR & FILTERS
# -----------------------------------------------------------------------------
st.sidebar.image("https://unmer.ac.id/wp-content/uploads/2020/07/Branding_Putih-300x118.png", width=100)
# Tampilkan Info User & Logout di Sidebar
user_name = getattr(st.user, "name", "User")
user_email = getattr(st.user, "email", "")

st.sidebar.markdown(f":material/person: **{user_name}**")
if user_email:
    st.sidebar.caption(user_email)

if st.sidebar.button(":material/logout: Logout", use_container_width=True):
    st.logout()

st.sidebar.title("UNMER Monitor")
st.sidebar.caption("Analisis Sentimen & Public Perception")
st.sidebar.markdown("---")

# Pipeline Control Expander (Versi Debugging)
with st.sidebar.expander(":material/settings: Pipeline Control", expanded=False):
    st.caption("Jalankan seluruh proses crawling & analisis data dari awal secara otomatis.")
    
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1").rstrip("/")
    
    PIPELINE_STEPS = [
        {"name": "1. Search Fetch", "endpoint": "/search/fetch/social"},
        {"name": "1.1 Search Fetch", "endpoint": "/search/fetch/reviews"},
        {"name": "1.2 Search Fetch", "endpoint": "/search/fetch/news"},
        {"name": "2. Scoring Process", "endpoint": "/score/process/social"},
        {"name": "3. Instagram Crawler", "endpoint": "/crawl/instagram"},
        {"name": "4. Tiktok Crawler", "endpoint": "/crawl/tiktok"},
        {"name": "5. Data Cleaning Instagram", "endpoint": "/clean/instagram"},
        {"name": "6. Data Cleaning Tiktok", "endpoint": "/clean/tiktok"},
        {"name": "7. Sentiment Analysis Instagram", "endpoint": "/sentiment/instagram"},
        {"name": "8. Sentiment Analysis Tiktok", "endpoint": "/sentiment/tiktok"},        
    ]

    if st.button(":material/rocket_launch: Jalankan Pipeline", type="primary", use_container_width=True):
        with st.status(":material/rocket_launch: Memproses...", expanded=True) as status:
            failed = False
            for step in PIPELINE_STEPS:
                url = f"{BACKEND_URL}{step['endpoint']}"
                st.write(f":material/sync: **{step['name']}**...")
                try:
                    res = requests.post(url, timeout=300)
                    
                    if res.status_code in [200, 201]:
                        st.write(f":material/check_circle: **{step['name']}** Selesai!")
                    else:
                        # Mengambil detail pesan error dari respons JSON backend
                        try:
                            err_detail = res.json().get("detail", res.text)
                        except Exception:
                            err_detail = res.text
                            
                        st.error(f":material/error: **{step['name']}** Gagal (HTTP {res.status_code}): {err_detail}")
                        failed = True
                        break
                        
                except requests.exceptions.Timeout:
                    st.error(f":material/error: **{step['name']}** Waktu habis (Timeout > 5 menit)")
                    failed = True
                    break
                except Exception as e:
                    st.error(f":material/error: Connection Error: {e}")
                    failed = True
                    break
            
            if not failed:
                status.update(label=":material/celebration: Selesai!", state="complete", expanded=False)
                st.success("Data berhasil diperbarui!")
                st.cache_data.clear()
                st.rerun()
            else:
                status.update(label=":material/warning: Terhenti Karena Error", state="error", expanded=True)

# # Pipeline Control Expander
# with st.sidebar.expander(":material/settings: Pipeline Control", expanded=False):
#     st.caption("Jalankan seluruh proses crawling & analisis data dari awal secara otomatis.")
    
#     BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1").rstrip("/")
    
#     PIPELINE_STEPS = [
#         {"name": "1. Search Fetch", "endpoint": "/search/fetch/social"},
#         {"name": "1.1 Search Fetch", "endpoint": "/search/fetch/reviews"},
#         {"name": "1.2 Search Fetch", "endpoint": "/search/fetch/news"},
#         {"name": "2. Scoring Process", "endpoint": "/score/process/social"},
#         {"name": "3. Instagram Crawler", "endpoint": "/crawl/instagram"},
#         {"name": "4. Tiktok Crawler", "endpoint": "/crawl/tiktok"},
#         {"name": "5. Data Cleaning Instagram", "endpoint": "/clean/instagram"},
#         {"name": "6. Data Cleaning Tiktok", "endpoint": "/clean/tiktok"},
#         {"name": "7. Sentiment Analysis Instagram", "endpoint": "/sentiment/instagram"},
#         {"name": "8. Sentiment Analysis Tiktok", "endpoint": "/sentiment/tiktok"},        
#     ]

#     if st.button(":material/rocket_launch: Jalankan Pipeline", type="primary", use_container_width=True):
#         with st.status(":material/rocket_launch: Memproses...", expanded=True) as status:
#             failed = False
#             for step in PIPELINE_STEPS:
#                 url = f"{BACKEND_URL}{step['endpoint']}"
#                 st.write(f":material/sync: **{step['name']}**...")
#                 try:
#                     res = requests.post(url, timeout=300)
#                     if res.status_code in [200, 201]:
#                         st.write(f":material/check_circle: **{step['name']}** Selesai!")
#                     else:
#                         st.error(f":material/error: **{step['name']}** Gagal ({res.status_code})")
#                         failed = True
#                         break
#                 except Exception as e:
#                     st.error(f":material/error: Connection Error: {e}")
#                     failed = True
#                     break
            
#             if not failed:
#                 status.update(label=":material/celebration: Selesai!", state="complete", expanded=False)
#                 st.success("Data berhasil diperbarui!")
#                 st.cache_data.clear()
#                 st.rerun()
#             else:
#                 status.update(label=":material/warning: Terhenti Karena Error", state="error", expanded=True)

# st.sidebar.markdown("---")

# Filter Platform
platform_filter = st.sidebar.multiselect(
    ":material/smartphone: Platform",
    options=["Instagram", "TikTok", "Google Review"],
    default=["Instagram", "TikTok", "Google Review"]
)

# Date Range Filter
date_filter_option = st.sidebar.selectbox(
    ":material/calendar_today: Rentang Waktu",
    ["Last 24 Hours", "Last 3 Days", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
    index=2
)

# Filter Sentiment Multi-select
sentiment_filter = st.sidebar.multiselect(
    ":material/label: Filter Sentimen",
    options=["positive", "neutral", "negative"],
    default=["positive", "neutral", "negative"]
)

# Search Box Keyword
search_query = st.sidebar.text_input(":material/search: Cari Kata Kunci Caption / Ulasan", "")

# Refresh Button
if st.sidebar.button(":material/sync: Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# -----------------------------------------------------------------------------
# 5. FILTERING LOGIC
# -----------------------------------------------------------------------------
if df_raw.empty:
    st.warning(":material/warning: Belum ada data analisis atau ulasan di database. Jalankan pipeline atau fetch data terlebih dahulu.")
    st.stop()

df_filtered = df_raw.copy()

# Platform Filter Logic
if platform_filter:
    df_filtered = df_filtered[df_filtered["platform"].isin(platform_filter)]

# Date Filtering Logic (WCAG: pd.Timestamp to avoid dtype mismatch)
now = pd.Timestamp.now(tz="UTC")
cutoff = None
if date_filter_option == "Last 24 Hours":
    cutoff = now - pd.Timedelta(hours=24)
elif date_filter_option == "Last 3 Days":
    cutoff = now - pd.Timedelta(days=3)
elif date_filter_option == "Last 7 Days":
    cutoff = now - pd.Timedelta(days=7)
elif date_filter_option == "Last 30 Days":
    cutoff = now - pd.Timedelta(days=30)
elif date_filter_option == "Last 90 Days":
    cutoff = now - pd.Timedelta(days=90)
if cutoff is not None:
    ts = pd.to_datetime(df_filtered["post_timestamp"], utc=True, errors="coerce")
    df_filtered = df_filtered[ts >= cutoff]

# Sentiment Filter Logic
if sentiment_filter:
    df_filtered = df_filtered[df_filtered["sentiment"].isin(sentiment_filter)]

# Search Keyword Logic
if search_query:
    df_filtered = df_filtered[df_filtered["caption"].str.contains(search_query, case=False, na=False)]

# -----------------------------------------------------------------------------
# 6. HEADER & KPI CARDS
# -----------------------------------------------------------------------------
st.title(":material/analytics: Cross-Platform Sentiment & Review Dashboard")

if not df_raw.empty and "analyzed_at" in df_raw.columns:
    last_updated_dt = df_raw["analyzed_at"].max()
    if pd.notnull(last_updated_dt):
        if last_updated_dt.tzinfo is None:
            waktu_str = last_updated_dt.tz_localize("UTC").tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M:%S WIB")
        else:
            waktu_str = last_updated_dt.tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M:%S WIB")
    else:
        waktu_str = "-"
else:
    waktu_str = "-"

st.caption(f"Menampilkan {len(df_filtered)} data gabungan (Instagram, TikTok, & Google Review) berdasarkan filter aktif. Terakhir diperbarui: {waktu_str}")

# KPI Metrics Calculation
total_posts = len(df_filtered)
total_likes = df_filtered["likes"].sum() if total_posts > 0 else 0
total_comments = df_filtered["comments"].sum() if total_posts > 0 else 0
pos_count = len(df_filtered[df_filtered["sentiment"] == "positive"])
pos_ratio = (pos_count / total_posts * 100) if total_posts > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Data / Post</div>
        <div class="metric-value">{total_posts:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Sentimen Positif</div>
        <div class="metric-value" style="color:#10b981;">{pos_ratio:.1f}%</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Likes</div>
        <div class="metric-value">{total_likes:,}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Komentar</div>
        <div class="metric-value">{total_comments:,}</div>
    </div>
    """, unsafe_allow_html=True)

# with col5:
#     avg_score = df_filtered["sentiment_score"].mean() if total_posts > 0 else 0.0
#     st.markdown(f"""
#     <div class="metric-card">
#         <div class="metric-label">Avg Score / Rating</div>
#         <div class="metric-value">{avg_score:.2f}</div>
#     </div>
#     """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. CHARTS & VISUALIZATIONS
# -----------------------------------------------------------------------------
chart_col1, chart_col2 = st.columns([1, 2])

with chart_col1:
    st.subheader(":material/donut_large: Distribusi Sentimen")
    if not df_filtered.empty:
        sentiment_counts = df_filtered["sentiment"].value_counts().reset_index()
        sentiment_counts.columns = ["sentiment", "count"]

        fig_pie = px.pie(
            sentiment_counts,
            values="count",
            names="sentiment",
            color="sentiment",
            color_discrete_map=COLOR_MAP,
            hole=0.55,
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=320)
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Tidak ada data untuk grafik.")

with chart_col2:
    st.subheader(":material/show_chart: Tren Sentimen dari Waktu ke Waktu")
    if not df_filtered.empty:
        df_trend = df_filtered.copy()
        df_trend["date"] = df_trend["post_timestamp"].dt.date
        trend_grouped = df_trend.groupby(["date", "sentiment"]).size().unstack(fill_value=0).reset_index()

        for s in ["positive", "neutral", "negative"]:
            if s not in trend_grouped.columns:
                trend_grouped[s] = 0

        fig_line = go.Figure()
        for s in ["positive", "neutral", "negative"]:
            fig_line.add_trace(go.Scatter(
                x=trend_grouped["date"],
                y=trend_grouped[s],
                mode='lines+markers',
                name=s.capitalize(),
                line=dict(color=COLOR_MAP[s], width=3),
                marker=dict(size=6)
            ))

        fig_line.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis_title="Tanggal",
            yaxis_title="Jumlah Data",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=320,
            hovermode="x unified"
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Tidak ada data untuk tren.")

# Platform Comparison Charts
comp_col1, comp_col2 = st.columns(2)

with comp_col1:
    st.subheader(":material/smartphone: Perbandingan Sentimen per Platform")
    if not df_filtered.empty:
        platform_sentiment = df_filtered.groupby(["platform", "sentiment"]).size().reset_index(name="count")
        fig_plat = px.bar(
            platform_sentiment,
            x="platform",
            y="count",
            color="sentiment",
            color_discrete_map=COLOR_MAP,
            barmode="group",
            labels={"platform": "Platform", "count": "Jumlah Data", "sentiment": "Sentimen"},
            height=300
        )
        fig_plat.update_layout(margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_plat, use_container_width=True)

with comp_col2:
    st.subheader(":material/local_fire_department: Rata-rata Interaksi Sosmed")
    if not df_filtered.empty:
        df_sosmed = df_filtered[df_filtered["platform"].isin(["Instagram", "TikTok"])]
        if not df_sosmed.empty:
            eng_platform = df_sosmed.groupby("platform")[["likes", "comments"]].mean().reset_index()
            fig_eng = px.bar(
                eng_platform,
                x="platform",
                y=["likes", "comments"],
                barmode="group",
                labels={"value": "Rata-rata Interaksi", "variable": "Metrik", "platform": "Platform"},
                color_discrete_sequence=["#3b82f6", "#ec4899"],
                height=300
            )
            fig_eng.update_layout(margin=dict(t=10, b=10, l=10, r=10))
            st.plotly_chart(fig_eng, use_container_width=True)
        else:
            st.info("Data sosmed tidak tersedia untuk perbandingan interaksi.")

# -----------------------------------------------------------------------------
# 8. POST FEED & DETAILED TABLE TABS (TERMASUK GOOGLE REVIEW)
# -----------------------------------------------------------------------------
st.markdown("---")
tab_feed, tab_reviews, tab_table = st.tabs([":material/smartphone: Feed Postingan", ":material/star: Google Reviews", ":material/table_view: Tabel Data Lengkap"])

with tab_feed:
    st.subheader("Feed Postingan Media Sosial (Instagram & TikTok)")
    df_social_feed = df_filtered[df_filtered["platform"].isin(["Instagram", "TikTok"])]

    if df_social_feed.empty:
        st.info("Tidak ada postingan sosmed yang sesuai kriteria filter.")
    else:
        ITEMS_PER_PAGE = 10
        total_items = len(df_social_feed)
        total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))

        if "social_page" not in st.session_state:
            st.session_state.social_page = 1

        if st.session_state.social_page > total_pages:
            st.session_state.social_page = 1

        start_idx = (st.session_state.social_page - 1) * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        df_page = df_social_feed.iloc[start_idx:end_idx]

        for _, row in df_page.iterrows():
            sentiment_class = f"badge-{row['sentiment']}"
            platform_badge = f"badge-{row['platform'].lower()}"
            views_val = row['views'] if pd.notnull(row['views']) else 0
            try: views_html = f"&nbsp;•&nbsp; :material/play_circle: {int(float(views_val)):,} Views" if views_val and float(views_val) > 0 else ""
            except: views_html=""

            st.markdown(f"""
            <div class="post-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div>
                        <span class="{platform_badge}">{row['platform']}</span>
                        <strong style="color:#e6f0e8; margin-left:6px;">@{row['username']}</strong>
                        <span style="color:#a8c0b0; font-size:12px; margin-left:8px;">
                            {row['post_timestamp'].strftime('%d %b %Y, %H:%M WIB') if pd.notnull(row['post_timestamp']) else ''}
                        </span>
                    </div>
                    <div>
                        <span class="{sentiment_class}">{row['sentiment'].upper()} ({row['sentiment_score']:.2f})</span>
                    </div>
                </div>
                <p style="color:#334155; font-size:14px; line-height:1.5; margin-bottom:10px;">
                    {
                        (row.get("caption") or "No caption available.")[:280]
                        + ("..." if len(row.get("caption") or "") > 280 else "")
                    }
                </p>
                <div style="background-color:#1a2e22; padding:10px 12px; border-radius:6px; font-size:14px; color:#d0e8d8; margin-bottom:10px; border:1px solid rgba(168,255,200,0.12);">
                    <span class="ms">lightbulb</span> <strong>Reasoning AI:</strong> {row['reasoning']}<br>
                    <span class="ms">analytics</span> <strong>Konteks Engagement:</strong> {row['engagement_context']}
                </div>
                <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; color:#a8c0b0;">
                    <div>
                        <span class="ms">favorite</span> {int(row['likes'] if pd.notnull(row['likes']) else 0):,} Likes &nbsp;•&nbsp; <span class="ms">chat_bubble</span> {int(row['comments'] if pd.notnull(row['comments']) else 0):,} Comments {views_html}
                    </div>
                    <div>
                        <a href="{row['post_url']}" target="_blank" style="color:#7affa8; text-decoration:none; font-weight:500;">
                            Buka di {row['platform']} <span class="ms">open_in_new</span>
                        </a>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button(":material/arrow_back: Sebelumnya (Sosmed)", disabled=(st.session_state.social_page == 1), use_container_width=True):
                st.session_state.social_page -= 1
                st.rerun()
        with col_info:
            st.markdown(
                f"<div style='text-align: center; padding-top: 6px; font-size: 14px; color: #64748b;'>"
                f"Halaman <b>{st.session_state.social_page}</b> dari <b>{total_pages}</b> "
                f"(Total <b>{total_items}</b> postingan)"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_next:
            if st.button("Selanjutnya :material/arrow_forward: (Sosmed)", disabled=(st.session_state.social_page == total_pages), use_container_width=True):
                st.session_state.social_page += 1
                st.rerun()

with tab_reviews:
    st.subheader(":material/star: Ulasan Google Maps (Google Reviews)")
    df_reviews_feed = df_filtered[df_filtered["platform"] == "Google Review"]

    if df_reviews_feed.empty:
        st.info("Tidak ada ulasan Google Maps yang sesuai kriteria filter.")
    else:
        ITEMS_PER_PAGE_REV = 10
        total_rev_items = len(df_reviews_feed)
        total_rev_pages = max(1, math.ceil(total_rev_items / ITEMS_PER_PAGE_REV))

        if "review_page" not in st.session_state:
            st.session_state.review_page = 1

        if st.session_state.review_page > total_rev_pages:
            st.session_state.review_page = 1

        start_idx_rev = (st.session_state.review_page - 1) * ITEMS_PER_PAGE_REV
        end_idx_rev = start_idx_rev + ITEMS_PER_PAGE_REV
        df_page_rev = df_reviews_feed.iloc[start_idx_rev:end_idx_rev]

        for _, row in df_page_rev.iterrows():
            sentiment_class = f"badge-{row['sentiment']}"
            rating_stars = '<span class="ms">star</span>' * int(row['rating']) if pd.notnull(row['rating']) else '<span class="ms">star</span> (N/A)'

            st.markdown(f"""
            <div class="post-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <div>
                        <span class="badge-google-review">Google Review</span>
                        <strong style="color:#e6f0e8; margin-left:6px;">{row['username']}</strong>
                        <span style="color:#a8c0b0; font-size:12px; margin-left:8px;">
                            {row['post_timestamp'].strftime('%d %b %Y, %H:%M WIB') if pd.notnull(row['post_timestamp']) else ''}
                        </span>
                    </div>
                    <div>
                        <span class="{sentiment_class}">{row['sentiment'].upper()}</span>
                    </div>
                </div>
                <div style="font-size:16px; margin-bottom:8px; color:#ffd600;">
                    {rating_stars} <span style="font-size:14px; font-weight:600; color:#a8c0b0;">({row['rating']}/5)</span>
                </div>
                <p style="color:#e6f0e8; font-size:15px; line-height:1.6; margin-bottom:10px;">
                    {row.get("caption") or "Tidak ada teks ulasan."}
                </p>
                <div style="background-color:#1a2e22; padding:10px 12px; border-radius:6px; font-size:14px; color:#d0e8d8; margin-bottom:10px; border:1px solid rgba(168,255,200,0.12);">
                    <span class="ms">lightbulb</span> <strong>Analisis / Catatan:</strong> {row['reasoning']}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        col_prev_r, col_info_r, col_next_r = st.columns([1, 2, 1])
        with col_prev_r:
            if st.button(":material/arrow_back: Sebelumnya (Reviews)", disabled=(st.session_state.review_page == 1), use_container_width=True):
                st.session_state.review_page -= 1
                st.rerun()
        with col_info_r:
            st.markdown(
                f"<div style='text-align: center; padding-top: 6px; font-size: 14px; color: #64748b;'>"
                f"Halaman <b>{st.session_state.review_page}</b> dari <b>{total_rev_pages}</b> "
                f"(Total <b>{total_rev_items}</b> ulasan)"
                f"</div>",
                unsafe_allow_html=True
            )
        with col_next_r:
            if st.button("Selanjutnya :material/arrow_forward: (Reviews)", disabled=(st.session_state.review_page == total_rev_pages), use_container_width=True):
                st.session_state.review_page += 1
                st.rerun()

with tab_table:
    st.subheader("Data Keseluruhan (Exportable)")
    if not df_filtered.empty:
        table_df = df_filtered[[
            "platform", "username", "sentiment", "sentiment_score", "rating", "likes", "comments", "views",
            "caption", "reasoning", "engagement_context", "post_url", "post_timestamp"
        ]]
        
        st.dataframe(
            table_df,
            column_config={
                "post_url": st.column_config.LinkColumn("Link / Referensi"),
                "sentiment_score": st.column_config.NumberColumn("Score", format="%.2f"),
                "rating": st.column_config.NumberColumn("Rating Bintang", format="%d"),
                "post_timestamp": st.column_config.DatetimeColumn("Waktu Data", format="DD/MM/YYYY HH:mm"),
            },
            use_container_width=True,
            hide_index=True
        )

        csv_data = table_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label=":material/download: Download Data CSV",
            data=csv_data,
            file_name=f"unmer_full_sentiment_reviews_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )