from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ---------------- Request schemas ----------------

class PromptCreate(BaseModel):
    name: str


class VersionCreate(BaseModel):
    content: str


class ExperimentRun(BaseModel):
    prompt_id: int
    input_text: str


# ---------------- Response schemas ----------------

class VersionResponse(BaseModel):
    id: int
    version_number: int
    content: str
    created_at: Optional[datetime] = None
    avg_score: Optional[float] = None

    class Config:
        from_attributes = True


class PromptResponse(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None
    version_count: int = 0

    class Config:
        from_attributes = True


class ResultResponse(BaseModel):
    id: int
    version_id: int
    output: str
    score: float
    latency: float

    class Config:
        from_attributes = True


class ExperimentResponse(BaseModel):
    id: int
    prompt_id: int
    input_text: str
    created_at: Optional[datetime] = None
    results: list[ResultResponse] = []

    class Config:
        from_attributes = True
