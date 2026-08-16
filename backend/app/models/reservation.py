from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ReservationStatus(str, Enum):
    RESERVED = "RESERVED"
    PICKED_UP = "PICKED_UP"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"


class ReservationCreate(BaseModel):
    location_id: str
    produce: str = Field(min_length=1, max_length=80)
    quantity: int = Field(gt=0, le=1000)


class Reservation(BaseModel):
    id: str
    location_id: str
    location_name: str
    location_address: str
    produce: str
    quantity: int
    created_at: datetime
    expires_at: datetime
    status: ReservationStatus
    user_id: Optional[str] = None
