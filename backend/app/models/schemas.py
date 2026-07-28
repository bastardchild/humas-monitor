# backend/app/models/schemas.py

import re
from pydantic import BaseModel, Field
from typing import Any, ClassVar, Dict, List, Optional
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
    """Model Pydantic untuk memproses & membersihkan caption Instagram & TikTok."""

    original_caption: str = ""
    cleaned_caption: str = ""
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    has_unmer_keyword: bool = False
    caption_length: int = 0
    word_count: int = 0

    # Gunakan ClassVar agar Pydantic tidak menganggapnya sebagai field instance
    OTHER_MALANG_CAMPUSES: ClassVar[List[str]] = [
        # Universitas Negeri Malang (UM)
        r"\buniversitas negeri malang\b",
        r"\b#universitasnegerimalang\b",
        r"\b#pkkmbum\d*\b",
        r"\b#mahasiswaum\b",
        r"\b#mabaum\b",
        # Universitas Brawijaya (UB)
        r"\buniversitas brawijaya\b",
        r"\b#universitasbrawijaya\b",
        r"\b#mahasiswaub\b",
        r"\b#ubmalang\b",
        # Universitas Muhammadiyah Malang (UMM)
        r"\buniversitas muhammadiyah malang\b",
        r"\b#universitasmuhammadiyahmalang\b",
        r"\b#umm\b",
        r"\b#ummmalang\b",
        # Politeknik Negeri Malang (POLINEMA)
        r"\bpoliteknik negeri malang\b",
        r"\b#polinema\b",
        r"\b#polinemamalang\b",
        # UIN Malang & Unisma
        r"\buin maulana malik ibrahim\b",
        r"\buin malang\b",
        r"\b#unisma\b",
    ]

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

        # 4. Validasi Kehadiran UNMER vs Kampus Lain
        lowered = text.lower()
        unmer_patterns = [r"\bunmer\b", r"\buniversitas merdeka\b", r"\bmerdeka malang\b", r"\bunmermalang\b"]
        
        has_unmer_explicit = any(re.search(pat, lowered) for pat in unmer_patterns)
        has_other_campus = any(re.search(pat, lowered) for pat in cls.OTHER_MALANG_CAMPUSES)

        # Flag `has_unmer_keyword` bernilai True HANYA JIKA:
        # Ada kata kunci UNMER DAN postingan tersebut tidak murni membahas kampus lain
        is_relevant_unmer = has_unmer_explicit and not (has_other_campus and not has_unmer_explicit)

        return cls(
            original_caption=text,
            cleaned_caption=cleaned,
            hashtags=hashtags,
            mentions=mentions,
            has_unmer_keyword=is_relevant_unmer,
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