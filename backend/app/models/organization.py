from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class OrganizationApplicationCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=140)
    organization_type: str = Field(min_length=2, max_length=80)
    address: str = Field(min_length=5, max_length=240)
    borough: str = Field(min_length=2, max_length=40)
    neighborhood: str = Field(min_length=2, max_length=80)
    contact_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(min_length=7, max_length=30)
    accepted_categories: list[str] = Field(min_length=1)
    opening_time: str
    closing_time: str
    notes: str = Field(default="", max_length=1000)


class OrganizationApplication(OrganizationApplicationCreate):
    id: str
    user_id: str
    email: str
    status: ApplicationStatus
    created_at: datetime
    location_id: Optional[str] = None
    review_note: str = ""


class ApprovalRequest(BaseModel):
    latitude: float = Field(ge=40.3, le=41.1)
    longitude: float = Field(ge=-74.4, le=-73.5)
    review_note: str = Field(default="Verified for NeedYield participation", max_length=500)


class RejectionRequest(BaseModel):
    review_note: str = Field(min_length=3, max_length=500)


class WeeklyNeedItem(BaseModel):
    produce_name: str = Field(min_length=2, max_length=80)
    need_level: str = Field(pattern="^(none|low|medium|high)$")
    requested_quantity: int = Field(default=0, ge=0, le=10000)


class WeeklyNeedsCreate(BaseModel):
    distribution_date: date
    accepting_donations: bool = True
    dropoff_start: str
    dropoff_end: str
    notes: str = Field(default="", max_length=1000)
    items: list[WeeklyNeedItem] = Field(min_length=1, max_length=50)


class WeeklyNeeds(WeeklyNeedsCreate):
    location_id: str
    submitted_at: datetime
