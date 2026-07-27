import re
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class SearchItem(BaseModel):
    keyword: str
    url: str
    title: Optional[str] = ""
    snippet: Optional[str] = ""
    raw_json: Dict[str, Any]

class RawResultDB(BaseModel):
    id: int
    keyword: str
    url: str
    title: Optional[str] = None
    snippet: Optional[str] = None
    created_at: datetime

class ScoringBreakdown(BaseModel):
    exact_match_found: bool = False
    unmer_malang_match: bool = False
    unmer_keyword_match: bool = False
    malang_context_match: bool = False
    base_points: int = 0
    matched_terms: List[str] = []

class ScoreOutput(BaseModel):
    raw_id: int
    url: str
    relevance_score: float = Field(..., ge=0.0, le=100.0)
    scoring_details: ScoringBreakdown

class CaptionCleaner(BaseModel):
    """Model Pydantic untuk memproses & membersihkan caption Instagram."""
    original_caption: str = ""
    cleaned_caption: str = ""
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    has_unmer_keyword: bool = False
    caption_length: int = 0
    word_count: int = 0

    @classmethod
    def clean(cls, raw_caption: Optional[str]) -> "CaptionCleaner":
        text = raw_caption or ""

        # 1. Ekstrak hashtags (#tag) dan mentions (@user)
        hashtags = re.findall(r"#(\w+)", text)
        mentions = re.findall(r"@(\w+)", text)

        # 2. Hapus URL/Link dari caption
        text_no_url = re.sub(r"https?://\S+|www\.\S+", "", text)

        # 3. Normalisasi spasi berlebih dan newlines
        cleaned = re.sub(r"\s+", " ", text_no_url).strip()

        # 4. Cek keberadaan kata kunci relevansi Universitas Merdeka Malang
        lowered = cleaned.lower()
        keywords = ["unmer", "universitas merdeka", "merdeka malang", "unmermalang"]
        has_kw = any(kw in lowered for kw in keywords)

        return cls(
            original_caption=text,
            cleaned_caption=cleaned,
            hashtags=hashtags,
            mentions=mentions,
            has_unmer_keyword=has_kw,
            caption_length=len(cleaned),
            word_count=len(cleaned.split()) if cleaned else 0
        )
    
class PostForAnalysis(BaseModel):
    instagram_post_id: int
    cleaned_caption_id: int
    caption: str
    likes_count: int
    comments_count: int

class SingleSentimentResult(BaseModel):
    instagram_post_id: int
    cleaned_caption_id: int
    sentiment: str = Field(..., description="positive, neutral, or negative")
    sentiment_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Penjelasan singkat max 1 kalimat")
    engagement_context: str = Field(..., description="Evaluasi singkat dampak likes dan comments")

class BatchSentimentResponse(BaseModel):
    results: List[SingleSentimentResult]