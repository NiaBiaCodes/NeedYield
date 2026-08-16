from fastapi import APIRouter
from app.models.rag import RagQuery, RagResponse
from app.services.rag_service import rag_service

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=RagResponse)
def query_resources(payload: RagQuery) -> RagResponse:
    return rag_service.query(payload)
