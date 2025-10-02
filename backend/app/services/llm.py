"""LLM service for interaction analysis using OpenRouter API."""

import json
from datetime import date

import httpx
import structlog

from backend.app.config import settings
from backend.app.models import (
    AnalyzeInteractionResponse,
    ExtractedContact,
    ExtractedFamilyMember,
    ExtractedInteraction,
)

logger = structlog.get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


EXTRACTION_PROMPT = """You are an AI assistant that extracts structured information from casual interaction notes.

Given the following text about an interaction with someone, extract:
1. Contact information (first name, last name, birthday if mentioned)
2. Interaction details (what happened, location, date)
3. Family members mentioned (names and relationships)

For each piece of information, provide a confidence score between 0.0 and 1.0.

Rules:
- If the interaction date is not explicitly mentioned, assume it's today's date: {today}
- If only a first name is mentioned, last_name should be null
- If no location is mentioned, location should be null
- If no family members are mentioned, return an empty list
- Be conservative with confidence scores - use lower scores when information is ambiguous

Return your response as a valid JSON object with this exact structure:
{{
    "contact": {{
        "first_name": "string or null",
        "last_name": "string or null",
        "birthday": "YYYY-MM-DD or null",
        "confidence": 0.0-1.0
    }},
    "interaction": {{
        "notes": "summary of what happened",
        "location": "string or null",
        "interaction_date": "YYYY-MM-DD",
        "confidence": 0.0-1.0
    }},
    "family_members": [
        {{
            "first_name": "string or null",
            "last_name": "string or null",
            "relationship": "spouse|child|parent|sibling|other",
            "confidence": 0.0-1.0
        }}
    ]
}}

Input text:
{text}

Respond ONLY with the JSON object, no additional text."""


async def analyze_interaction(text: str) -> AnalyzeInteractionResponse:
    """
    Analyze interaction text using OpenRouter API to extract structured data.

    Args:
        text: Raw interaction text

    Returns:
        Analyzed interaction with extracted fields and confidence scores

    Raises:
        httpx.HTTPError: If API request fails
        ValueError: If API response is invalid
    """
    logger.info("analyzing_interaction", text_length=len(text))

    today = date.today().isoformat()
    prompt = EXTRACTION_PROMPT.format(today=today, text=text)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://github.com/memoro",
                    "X-Title": "Memoro",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-3.5-sonnet",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,  # Low temperature for more consistent extraction
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            logger.debug("openrouter_response", response=data)

            # Extract the content from OpenRouter response
            content = data["choices"][0]["message"]["content"]

            # Parse the JSON response
            extracted_data = json.loads(content)

            # Build response model
            result = AnalyzeInteractionResponse(
                contact=ExtractedContact(**extracted_data["contact"]),
                interaction=ExtractedInteraction(**extracted_data["interaction"]),
                family_members=[
                    ExtractedFamilyMember(**fm) for fm in extracted_data.get("family_members", [])
                ],
                raw_text=text,
            )

            logger.info(
                "interaction_analyzed",
                contact_name=f"{result.contact.first_name} {result.contact.last_name}",
                family_members_count=len(result.family_members),
            )

            return result

        except httpx.HTTPError as e:
            logger.error("openrouter_http_error", error=str(e))
            raise
        except (KeyError, json.JSONDecodeError, ValueError) as e:
            logger.error("openrouter_parse_error", error=str(e), content=content if "content" in locals() else None)
            raise ValueError(f"Failed to parse OpenRouter response: {e}") from e
