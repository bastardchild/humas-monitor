-- Supabase tables mirrored in SQLite
CREATE TABLE IF NOT EXISTS raw_search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT, url TEXT, title TEXT, snippet TEXT, raw_json TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS raw_news_search_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT, url TEXT, title TEXT, snippet TEXT, raw_json TEXT, created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS raw_google_reviews (id INTEGER PRIMARY KEY AUTOINCREMENT, place_id TEXT, review_json TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS instagram_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, raw_id INTEGER, post_url TEXT UNIQUE, short_code TEXT, shortcode TEXT, owner_username TEXT, caption TEXT, likes_count INTEGER, comments_count INTEGER, post_timestamp TEXT, raw_json TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS tiktok_posts (id INTEGER PRIMARY KEY AUTOINCREMENT, raw_id INTEGER, post_url TEXT UNIQUE, video_id TEXT, owner_username TEXT, owner_nickname TEXT, caption TEXT, likes_count INTEGER, comments_count INTEGER, shares_count INTEGER, plays_count INTEGER, post_timestamp TEXT, raw_json TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS news_articles (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT UNIQUE, title TEXT, description TEXT, content_markdown TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS cleaned_instagram_captions (id INTEGER PRIMARY KEY AUTOINCREMENT, post_url TEXT, cleaned_caption TEXT, hashtags TEXT, mentions TEXT, has_unmer_keyword INTEGER, created_at TEXT DEFAULT (datetime('now')), UNIQUE(post_url));
CREATE TABLE IF NOT EXISTS cleaned_tiktok_captions (id INTEGER PRIMARY KEY AUTOINCREMENT, post_url TEXT, cleaned_caption TEXT, hashtags TEXT, mentions TEXT, has_unmer_keyword INTEGER, created_at TEXT DEFAULT (datetime('now')), UNIQUE(post_url));
CREATE TABLE IF NOT EXISTS scored_results (raw_id INTEGER PRIMARY KEY, score REAL, scoring_details TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS scored_news_results (raw_news_id INTEGER PRIMARY KEY, score REAL, scoring_details TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS scored_news_articles_l2 (id INTEGER PRIMARY KEY, url TEXT UNIQUE, score REAL, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS sentiment_analysis_results (id INTEGER PRIMARY KEY AUTOINCREMENT, post_url TEXT UNIQUE, sentiment TEXT, sentiment_score REAL, reasoning TEXT, created_at TEXT DEFAULT (datetime('now')));
CREATE TABLE IF NOT EXISTS tiktok_sentiment_analysis_results (id INTEGER PRIMARY KEY AUTOINCREMENT, post_url TEXT UNIQUE, sentiment TEXT, sentiment_score REAL, reasoning TEXT, created_at TEXT DEFAULT (datetime('now')));
