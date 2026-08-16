from pydantic import BaseModel, Field


class ProduceItem(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=10_000)
    unit: str = Field(default="count", max_length=30)


class AnalyzedProduceItem(BaseModel):
    name: str
    estimated_quantity: int = Field(ge=0)
    confidence: float = Field(ge=0, le=1)


class ProduceAnalysisResponse(BaseModel):
    items: list[AnalyzedProduceItem]
    source: str
    review_recommended: bool = True
    message: str


class GeminiProduceAnalysis(BaseModel):
    items: list[AnalyzedProduceItem]
