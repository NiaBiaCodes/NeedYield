import json
import logging
import os
from app.models.produce import GeminiProduceAnalysis, ProduceAnalysisResponse

logger = logging.getLogger(__name__)


async def analyze_image(image_bytes: bytes, mime_type: str) -> ProduceAnalysisResponse:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    "Please analyze the attached image: 1. What produce is in this picture? 2. Count all visible produce items. Ignore leaves and foliage—focus only on the fruit/vegetable items. 3. List each item by its relative location in the image, then state the final total count. Identify visible produce and estimate counts. Return JSON only with items containing name, estimated_quantity, and confidence. Do not assess food safety.",
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiProduceAnalysis,
                ),
            )
            payload = GeminiProduceAnalysis.model_validate_json(response.text)
            items = payload.items
            if items:
                return ProduceAnalysisResponse(items=items, source="gemini", review_recommended=any(i.confidence < 0.8 for i in items), message="AI quantities are estimates. Confirm your harvest before continuing.")
            logger.warning("Gemini image analysis returned no produce items")
        except Exception as error:
            logger.warning("Gemini image analysis failed (%s): %s", type(error).__name__, error)
    return ProduceAnalysisResponse(
        items=[],
        source="mock_fallback",
        review_recommended=True,
        message="We couldn't confidently analyze this photo. Enter your produce manually.",
    )
