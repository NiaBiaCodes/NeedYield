from typing import Optional
from pydantic import BaseModel, Field


class RagQuery(BaseModel):
    query: str = Field(min_length=3, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class RagRecommendation(BaseModel):
    resource_id: str
    name: str
    address: str
    neighborhood: str
    borough: str
    hours: str
    available_inventory: dict[str, int]
    distance_miles: Optional[float] = None
    reasons: list[str]


class RagSource(BaseModel):
    resource_id: str
    name: str
    source: str
    source_url: Optional[str] = None


class RagResponse(BaseModel):
    answer: str
    recommendations: list[RagRecommendation]
    sources: list[RagSource]
    retrieved_count: int
    retrieval_mode: str
    generation_mode: str
    fallback: bool
