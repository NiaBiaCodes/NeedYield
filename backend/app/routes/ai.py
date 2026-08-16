from fastapi import APIRouter, File, HTTPException, UploadFile
from app.models.produce import ProduceAnalysisResponse
from app.services.ai_service import analyze_image

router = APIRouter(prefix="/api", tags=["ai"])
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_BYTES = 8 * 1024 * 1024


@router.post("/analyze-produce", response_model=ProduceAnalysisResponse)
async def analyze_produce(image: UploadFile = File(...)) -> ProduceAnalysisResponse:
    if image.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Upload a JPEG, PNG, or WEBP image")
    data = await image.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "Image must be 8 MB or smaller")
    if not data:
        raise HTTPException(400, "Image is empty")
    return await analyze_image(data, image.content_type)

