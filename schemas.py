from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# ---------------- REQUEST SCHEMAS ----------------

class PromptCreate(BaseModel):
    name: str


class VersionCreate(BaseModel):
    content: str


class ExperimentRun(BaseModel):
    prompt_id: int
    input_text: str


# ---------------- RESPONSE SCHEMAS ----------------

class ScoresDetail(BaseModel):
    clarity: float
    relevance: float
    grammar: float
    depth: float   # ✅ FIXED (was composite before)


class VersionResponse(BaseModel):
    id: int
    version_number: int
    content: str
    created_at: Optional[datetime] = None
    avg_score: Optional[float] = None
    run_count: int = 0

    class Config:
        from_attributes = True


class PromptResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None
    version_count: int = 0
    experiment_count: int = 0

    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    id: int
    version_id: int
    output: str
    score: float

    # Per-metric scores
    clarity_score: Optional[float] = None
    relevance_score: Optional[float] = None
    grammar_score: Optional[float] = None
    depth_score: Optional[float] = None   # ✅ FIXED

    latency: float

    class Config:
        from_attributes = True


class ExperimentResponse(BaseModel):
    id: int
    prompt_id: int
    input_text: str
    created_at: Optional[datetime] = None

    # Safe default (no mutable bug)
    results: List[ResultResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
