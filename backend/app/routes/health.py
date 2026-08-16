from fastapi import APIRouter
from app.services.database_service import database_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "storage": database_service.mode}
