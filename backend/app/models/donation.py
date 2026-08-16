from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from .produce import ProduceItem


class DonationStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZED = "ANALYZED"
    MATCHED = "MATCHED"
    CONFIRMED = "CONFIRMED"
    DELIVERED = "DELIVERED"


class MatchRequest(BaseModel):
    gardener_latitude: float
    gardener_longitude: float
    preferred_location_id: str
    preferred_radius_miles: float = Field(gt=0, le=50)
    items: list[ProduceItem]


class Allocation(BaseModel):
    location_id: str
    location_name: str
    produce: str
    quantity: int = Field(ge=0, le=10_000)
    score: float
    distance_miles: float
    preferred: bool = False
    reasons: list[str]


class MatchResponse(BaseModel):
    preferred_allocations: list[Allocation]
    recommended_allocations: list[Allocation]
    remaining_surplus: dict[str, int]
    surplus_alert: bool
    data_source: str


class ConfirmDonationRequest(BaseModel):
    gardener_id: str = "demo-gardener"
    preferred_location_id: str
    preferred_radius_miles: float
    items: list[ProduceItem]
    allocations: list[Allocation]


class Donation(BaseModel):
    id: str
    gardener_id: str
    timestamp: datetime
    preferred_location_id: str
    preferred_radius_miles: float
    items: list[ProduceItem]
    allocations: list[Allocation]
    status: DonationStatus
