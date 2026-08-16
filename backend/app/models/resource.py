from typing import Optional

from pydantic import BaseModel, Field


class PublicResource(BaseModel):
    id: str
    name: str
    resource_type: str
    address: str
    borough: str
    neighborhood: str
    latitude: float
    longitude: float
    website: Optional[str] = None
    description: Optional[str] = None
    source: str
    source_dataset_id: str
    verified_partner: bool = False
    donation_acceptance_verified: bool = False
    matched_terms: list[str] = Field(default_factory=list)
    food_relevance_score: int = 0
    acceptance_note: str = "Contact this resource before bringing food."
    operating_information: Optional[str] = None


class PublicResourceResponse(BaseModel):
    resources: list[PublicResource]
    source: str
    dataset_id: str
    fallback: bool
