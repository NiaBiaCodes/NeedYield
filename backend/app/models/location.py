from pydantic import BaseModel


class Location(BaseModel):
    id: str
    name: str
    address: str
    borough: str
    neighborhood: str
    latitude: float
    longitude: float
    opening_time: str
    closing_time: str
    accepted_categories: list[str]
    saturday_needs: dict[str, str]
    requested_quantities: dict[str, int] = {}
    inventory: dict[str, int]
    verified_partner: bool
    participating: bool
    accepts_saturday: bool
    demo: bool
    community_need_score: float
    community_need_source: str

