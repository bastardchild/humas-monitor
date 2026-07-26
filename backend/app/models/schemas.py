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
