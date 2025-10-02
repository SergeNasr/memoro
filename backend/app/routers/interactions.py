"""Interaction endpoints."""

import structlog
from fastapi import APIRouter, HTTPException, status

from backend.app.models import AnalyzeInteractionRequest, AnalyzeInteractionResponse
from backend.app.services.llm import analyze_interaction

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("/analyze", response_model=AnalyzeInteractionResponse, status_code=status.HTTP_200_OK)
async def analyze_interaction_endpoint(request: AnalyzeInteractionRequest) -> AnalyzeInteractionResponse:
    """
    Analyze raw interaction text and extract structured information.

    This endpoint uses LLM to extract:
    - Contact information (name, birthday)
    - Interaction details (notes, location, date)
    - Family members mentioned

    Each extracted field includes a confidence score.
    """
    try:
        result = await analyze_interaction(request.text)
        return result
    except Exception as e:
        logger.error("analyze_interaction_failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to analyze interaction. Please try again.",
        ) from e
