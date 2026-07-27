import os
import requests
import math
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

# -----------------------------------------------------------------------------
# 1. PAGE CONFIG & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="UNMER Monitor - Sentiment Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS untuk UI Modern & Card Metrics
st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    .metric-card {
        background-color: #ffffff;
        padding: 18px 22px;
        border-radius: 12px;
        border: 1px solid #e9ecef;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1e293b;
    }
    .metric-label {
        font-size: 13px;
        color: #64748b;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-positive {
        background-color: #d1fae5; color: #065f46; 
        padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 12px;
    }
    .badge-neutral {
        background-color: #fef3c7; color: #92400e; 
        padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 12px;
    }
    .badge-negative {
        background-color: #fee2e2; color: #991b1b; 
        padding: 4px 10px; border-radius: 20px; font-weight: 600; font-size: 12px;
    }
    .post-card {
        background: #ffffff;
        border-radius: 10px;
        padding: 16px;
        margin-bottom: 12px;
        border: 1px solid #e2e8f0;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. SUPABASE CONNECTION
# -----------------------------------------------------------------------------
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

@st.cache_resource
def init_supabase() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("⚠️ SUPABASE_URL atau SUPABASE_KEY belum diatur di file .env")
        st.stop()
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

# COLOR PALETTE
COLOR_MAP = {
    "positive": "#10b981",  # Emerald Green
    "neutral": "#f59e0b",   # Amber
    "negative": "#ef4444"   # Red
}

# -----------------------------------------------------------------------------
# 3. DATA FETCHING
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60)
def fetch_sentiment_data() -> pd.DataFrame:
    """Mengambil data hasil analisis sentimen beserta relational post data."""
    try:
        response = supabase.table("sentiment_analysis_results").select("""
            id,
            sentiment,
            sentiment_score,
            reasoning,
            engagement_context,
            analyzed_at,
            instagram_posts (
                id,
                post_url,
                owner_username,
                likes_count,
                comments_count,
                post_timestamp
            ),
            cleaned_instagram_captions (
                cleaned_caption,
                hashtags
            )
        """).execute()

        rows = response.data or []
        if not rows:
            return pd.DataFrame()

        flattened = []
        for r in rows:
            ig = r.get("instagram_posts") or {}
            cleaned = r.get("cleaned_instagram_captions") or {}
            
            flattened.append({
                "id": r["id"],
                "sentiment": (r.get("sentiment") or "neutral").lower(),
                "sentiment_score": r.get("sentiment_score", 0.5),
                "reasoning": r.get("reasoning", ""),
                "engagement_context": r.get("engagement_context", ""),
                "analyzed_at": pd.to_datetime(r.get("analyzed_at")),
                "post_url": ig.get("post_url", "#"),
                "username": ig.get("owner_username") or "Unknown",
                "likes": ig.get("likes_count", 0),
                "comments": ig.get("comments_count", 0),
                "total_engagement": ig.get("likes_count", 0) + ig.get("comments_count", 0),
                "post_timestamp": pd.to_datetime(ig.get("post_timestamp")) if ig.get("post_timestamp") else pd.to_datetime(r.get("analyzed_at")),
                "caption": cleaned.get("cleaned_caption", ""),
                "hashtags": cleaned.get("hashtags", [])
            })

        df = pd.DataFrame(flattened)
        return df

    except Exception as e:
        st.error(f"Gagal mengambil data dari Supabase: {e}")
        return pd.DataFrame()

df_raw = fetch_sentiment_data()

# -----------------------------------------------------------------------------
# 4. SIDEBAR & FILTERS
# -----------------------------------------------------------------------------
st.sidebar.image("https://unmer.ac.id/wp-content/uploads/2020/07/Branding_Putih-300x118.png", width=100)
st.sidebar.title("UNMER Monitor")
st.sidebar.caption("Analisis Sentimen & Public Perception")
st.sidebar.markdown("---")

# =============================================================================
# 🔥 KODE PIPELINE BUTTON DITARUH DI SINI (Di dalam Expander Sidebar)
# =============================================================================
with st.sidebar.expander("⚙️ Pipeline Control", expanded=False):
    st.caption("Jalankan seluruh proses crawling & analisis data dari awal secara otomatis.")
    
    # URL Backend dari .env atau default localhost
    BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1").rstrip("/")
    
    PIPELINE_STEPS = [
        {"name": "1. Search Fetch", "endpoint": "/search/fetch"},
        {"name": "2. Scoring Process", "endpoint": "/score/process"},
        {"name": "3. Instagram Crawler", "endpoint": "/crawl/instagram"},
        {"name": "4. Data Cleaning", "endpoint": "/clean/captions"},
        {"name": "5. Sentiment Analysis", "endpoint": "/sentiment/analyze"},
    ]

    if st.button("🚀 Jalankan Pipeline", type="primary", use_container_width=True):
        with st.status("🚀 Memproses...", expanded=True) as status:
            failed = False
            for step in PIPELINE_STEPS:
                url = f"{BACKEND_URL}{step['endpoint']}"
                st.write(f"🔄 **{step['name']}**...")
                try:
                    res = requests.post(url, timeout=300)
                    if res.status_code in [200, 201]:
                        st.write(f"✅ **{step['name']}** Selesai!")
                    else:
                        st.error(f"❌ **{step['name']}** Gagal ({res.status_code})")
                        failed = True
                        break
                except Exception as e:
                    st.error(f"❌ Connection Error: {e}")
                    failed = True
                    break
            
            if not failed:
                status.update(label="🎉 Selesai!", state="complete", expanded=False)
                st.success("Data berhasil diperbarui!")
                st.cache_data.clear()
                st.rerun()
            else:
                status.update(label="⚠️ Terhenti Karena Error", state="error", expanded=True)

st.sidebar.markdown("---")

# Date Range Filter
date_filter_option = st.sidebar.selectbox(
    "📅 Rentang Waktu",
    ["Last 24 Hours", "Last 3 Days", "Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
    index=2
)

# Filter Sentiment Multi-select
sentiment_filter = st.sidebar.multiselect(
    "🏷️ Filter Sentimen",
    options=["positive", "neutral", "negative"],
    default=["positive", "neutral", "negative"]
)

# Search Box Keyword
search_query = st.sidebar.text_input("🔍 Cari Kata Kunci Caption", "")

# Refresh Button
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear()
    st.rerun()

# -----------------------------------------------------------------------------
# 5. FILTERING LOGIC
# -----------------------------------------------------------------------------
if df_raw.empty:
    st.warning("⚠️ Belum ada data analisis sentimen di database. Jalankan pipeline analisis terlebih dahulu.")
    st.stop()

df_filtered = df_raw.copy()

# Date Filtering Logic
now = datetime.now(timezone.utc)
if date_filter_option == "Last 24 Hours":
    cutoff = now - timedelta(hours=24)
    df_filtered = df_filtered[df_filtered["post_timestamp"] >= cutoff]
elif date_filter_option == "Last 3 Days":
    cutoff = now - timedelta(days=3)
    df_filtered = df_filtered[df_filtered["post_timestamp"] >= cutoff]
elif date_filter_option == "Last 7 Days":
    cutoff = now - timedelta(days=7)
    df_filtered = df_filtered[df_filtered["post_timestamp"] >= cutoff]
elif date_filter_option == "Last 30 Days":
    cutoff = now - timedelta(days=30)
    df_filtered = df_filtered[df_filtered["post_timestamp"] >= cutoff]
elif date_filter_option == "Last 90 Days":
    cutoff = now - timedelta(days=90)
    df_filtered = df_filtered[df_filtered["post_timestamp"] >= cutoff]

# Sentiment Filter Logic
if sentiment_filter:
    df_filtered = df_filtered[df_filtered["sentiment"].isin(sentiment_filter)]

# Search Keyword Logic
if search_query:
    df_filtered = df_filtered[df_filtered["caption"].str.contains(search_query, case=False, na=False)]

# -----------------------------------------------------------------------------
# 6. HEADER & KPI CARDS
# -----------------------------------------------------------------------------
st.title("📊 Instagram Sentiment Dashboard")

# --- HITUNG WAKTU TERAKHIR DIPERBARUI DARI DATA SUPABASE ---
if not df_raw.empty and "analyzed_at" in df_raw.columns:
    # Ambil timestamp analisis terbaru dari Supabase
    last_updated_dt = df_raw["analyzed_at"].max()
    
    # Konversi ke Waktu Indonesia Barat (WIB)
    if last_updated_dt.tzinfo is None:
        waktu_str = last_updated_dt.tz_localize("UTC").tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M:%S WIB")
    else:
        waktu_str = last_updated_dt.tz_convert("Asia/Jakarta").strftime("%d %b %Y, %H:%M:%S WIB")
else:
    waktu_str = "-"

# Tampilkan caption dengan waktu asli dari Supabase
st.caption(f"Menampilkan {len(df_filtered)} postingan berdasarkan filter aktif. Terakhir diperbarui di database: {waktu_str}")

# KPI Metrics Calculation
total_posts = len(df_filtered)
total_likes = df_filtered["likes"].sum() if total_posts > 0 else 0
total_comments = df_filtered["comments"].sum() if total_posts > 0 else 0
pos_count = len(df_filtered[df_filtered["sentiment"] == "positive"])
pos_ratio = (pos_count / total_posts * 100) if total_posts > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Total Postingan</div>
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

with col5:
    avg_score = df_filtered["sentiment_score"].mean() if total_posts > 0 else 0.0
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Avg Confidence</div>
        <div class="metric-value">{avg_score:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 7. CHARTS & VISUALIZATIONS
# -----------------------------------------------------------------------------
chart_col1, chart_col2 = st.columns([1, 2])

with chart_col1:
    st.subheader("🍩 Distribusi Sentimen")
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
    st.subheader("📈 Tren Sentimen dari Waktu ke Waktu")
    if not df_filtered.empty:
        # Grouping berdasarkan Tanggal
        df_trend = df_filtered.copy()
        df_trend["date"] = df_trend["post_timestamp"].dt.date
        trend_grouped = df_trend.groupby(["date", "sentiment"]).size().unstack(fill_value=0).reset_index()

        # Re-ensure all sentiment columns exist
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
            yaxis_title="Jumlah Postingan",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=320,
            hovermode="x unified"
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Tidak ada data untuk tren.")

# Engagement Comparison Chart
st.subheader("🔥 Evaluasi Engagement Berdasarkan Sentimen")
if not df_filtered.empty:
    eng_grouped = df_filtered.groupby("sentiment")[["likes", "comments"]].mean().reset_index()
    fig_bar = px.bar(
        eng_grouped,
        x="sentiment",
        y=["likes", "comments"],
        barmode="group",
        labels={"value": "Rata-rata Interaksi", "variable": "Metrik", "sentiment": "Sentimen"},
        color_discrete_sequence=["#3b82f6", "#ec4899"],
        height=300
    )
    fig_bar.update_layout(margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig_bar, use_container_width=True)

# -----------------------------------------------------------------------------
# 8. POST FEED & DETAILED TABLE
# -----------------------------------------------------------------------------
st.markdown("---")
tab_feed, tab_table = st.tabs(["📱 Feed Postingan Instagram", "📋 Tabel Data Lengkap"])

with tab_feed:
    st.subheader("Feed Postingan Teranalisis")

if df_filtered.empty:
    st.info("Tidak ada postingan yang sesuai kriteria filter.")
else:
    # -------------------------------------------------------------------------
    # KONFIGURASI PAGINATION (10 Data Per Halaman)
    # -------------------------------------------------------------------------
    ITEMS_PER_PAGE = 10
    total_items = len(df_filtered)
    total_pages = max(1, math.ceil(total_items / ITEMS_PER_PAGE))

    # Inisialisasi halaman saat ini di session_state jika belum ada
    if "current_page" not in st.session_state:
        st.session_state.current_page = 1

    # Jaga-jaga jika filter diubah dan halaman aktif melebihi total_pages baru
    if st.session_state.current_page > total_pages:
        st.session_state.current_page = 1

    # Hitung indeks awal dan akhir data yang akan ditampilkan
    start_idx = (st.session_state.current_page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    df_page = df_filtered.iloc[start_idx:end_idx]

    # -------------------------------------------------------------------------
    # LOOP TAMPILKAN DATA PADA HALAMAN AKTIF
    # -------------------------------------------------------------------------
    for _, row in df_page.iterrows():
        sentiment_class = f"badge-{row['sentiment']}"
        
        st.markdown(f"""
        <div class="post-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                <div>
                    <strong style="color:#94a3b8;">@{row['username']}</strong>
                    <span style="color:#94a3b8; font-size:12px; margin-left:8px;">
                        {row['post_timestamp'].strftime('%d %b %Y, %H:%M WIB') if pd.notnull(row['post_timestamp']) else ''}
                    </span>
                </div>
                <div>
                    <span class="{sentiment_class}">{row['sentiment'].upper()} ({row['sentiment_score']:.2f})</span>
                </div>
            </div>
            <p style="color:#334155; font-size:14px; line-height:1.5; margin-bottom:10px;">
                {row['caption'][:280] + ('...' if len(row['caption']) > 280 else '')}
            </p>
            <div style="background-color:#f1f5f9; padding:8px 12px; border-radius:6px; font-size:12px; color:#475569; margin-bottom:10px;">
                💡 <strong>Reasoning AI:</strong> {row['reasoning']}<br>
                📊 <strong>Konteks Engagement:</strong> {row['engagement_context']}
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px; color:#64748b;">
                <div>
                    ❤️ {row['likes']:,} Likes &nbsp;•&nbsp; 💬 {row['comments']:,} Comments
                </div>
                <div>
                    <a href="{row['post_url']}" target="_blank" style="color:#2563eb; text-decoration:none; font-weight:500;">
                        Buka di Instagram ↗
                    </a>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # NAVIGASI PAGINATION (Tombol Prev / Next)
    # -------------------------------------------------------------------------
    st.markdown("---")
    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if st.button("⬅️ Sebelumnya", disabled=(st.session_state.current_page == 1), use_container_width=True):
            st.session_state.current_page -= 1
            st.rerun()

    with col_info:
        st.markdown(
            f"<div style='text-align: center; padding-top: 6px; font-size: 14px; color: #64748b;'>"
            f"Halaman <b>{st.session_state.current_page}</b> dari <b>{total_pages}</b> "
            f"(Total <b>{total_items}</b> postingan)"
            f"</div>",
            unsafe_allow_html=True
        )

    with col_next:
        if st.button("Selanjutnya ➡️", disabled=(st.session_state.current_page == total_pages), use_container_width=True):
            st.session_state.current_page += 1
            st.rerun()

with tab_table:
    st.subheader("Data Analisis Sentimen (Exportable)")
    if not df_filtered.empty:
        table_df = df_filtered[[
            "username", "sentiment", "sentiment_score", "likes", "comments", 
            "caption", "reasoning", "engagement_context", "post_url", "post_timestamp"
        ]]
        
        st.dataframe(
            table_df,
            column_config={
                "post_url": st.column_config.LinkColumn("Instagram Link"),
                "sentiment_score": st.column_config.NumberColumn("Score", format="%.2f"),
                "post_timestamp": st.column_config.DatetimeColumn("Waktu Post", format="DD/MM/YYYY HH:mm"),
            },
            use_container_width=True,
            hide_index=True
        )

        # Download CSV Button
        csv_data = table_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Data CSV",
            data=csv_data,
            file_name=f"unmer_sentiment_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )