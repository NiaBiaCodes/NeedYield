from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class OrganizationAssistantIntent(str, Enum):
    INVENTORY_STATUS = "inventory_status"
    LOW_STOCK = "low_stock"
    INCOMING_DONATIONS = "incoming_donations"
    WEEKLY_NEEDS = "weekly_needs"
    RECOMMENDED_REQUESTS = "recommended_requests"
    PENDING_ACTIONS = "pending_actions"
    DAILY_SUMMARY = "daily_summary"
    PICKUP_STATUS = "pickup_status"
    GENERAL = "general_need_yield_question"


class OrganizationAssistantQuery(BaseModel):
    query: str = Field(min_length=3, max_length=500)


class InventoryStatusItem(BaseModel):
    produce_name: str
    available_quantity: int
    weekly_target: Optional[int] = None
    confirmed_donation_quantity: int = 0
    reserved_quantity: int = 0
    projected_shortage: Optional[int] = None
    unit: str = "count"


class OrganizationDonationSummary(BaseModel):
    donation_id: str
    gardener_id: str
    produce_name: str
    quantity: int
    confirmed_at: str
    status: str
    unit: str = "count"


class OrganizationActionItem(BaseModel):
    id: str
    kind: str
    title: str
    detail: str
    urgency: int = Field(ge=1, le=5)
    action: Optional[str] = None
    produce_name: Optional[str] = None
    suggested_quantity: Optional[int] = None


class OrganizationTodayStatus(BaseModel):
    confirmed_donations: int
    low_stock_items: int
    outstanding_actions: int
    reserved_for_distribution: int
    unit: str = "count"


class OrganizationAssistantResponse(BaseModel):
    intent: OrganizationAssistantIntent
    organization_name: str
    location_id: str
    demo: bool
    summary: str
    today: OrganizationTodayStatus
    inventory: list[InventoryStatusItem] = Field(default_factory=list)
    donations: list[OrganizationDonationSummary] = Field(default_factory=list)
    actions: list[OrganizationActionItem] = Field(default_factory=list)
    generation_mode: str = "deterministic"
    fallback: bool = False
