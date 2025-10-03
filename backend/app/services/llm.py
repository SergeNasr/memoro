"""LLM service for interaction analysis using OpenRouter API."""

import json
from datetime import date
from pathlib import Path

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


def load_prompt(filename: str) -> str:
    """
    Load LLM prompt from file.

    Args:
        filename: Path relative to backend/app/prompts/ directory

    Returns:
        Prompt text

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    prompts_dir = Path(__file__).parent.parent / "prompts"
    prompt_path = prompts_dir / filename

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path.read_text()


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
    prompt_template = load_prompt("extract_interaction.txt")
    prompt = prompt_template.format(today=today, text=text)

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
            logger.error(
                "openrouter_parse_error",
                error=str(e),
                content=content if "content" in locals() else None,
            )
            raise ValueError(f"Failed to parse OpenRouter response: {e}") from e
