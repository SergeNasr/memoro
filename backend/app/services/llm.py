"""LLM service for interaction analysis using OpenAI API."""

from datetime import date
from pathlib import Path

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.models import (
    AnalyzeInteractionResponse,
    ExtractedContact,
    ExtractedFamilyMember,
    ExtractedInteraction,
)

logger = structlog.get_logger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)


class ExtractionResult(BaseModel):
    """Structured extraction result for OpenAI API."""

    contact: ExtractedContact
    interaction: ExtractedInteraction
    family_members: list[ExtractedFamilyMember] = Field(default_factory=list)


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
    Analyze interaction text using OpenAI API to extract structured data.

    Args:
        text: Raw interaction text

    Returns:
        Analyzed interaction with extracted fields and confidence scores

    Raises:
        Exception: If API request or parsing fails
    """
    logger.info("analyzing_interaction", text_length=len(text))

    today = date.today().isoformat()
    prompt_template = load_prompt("extract_interaction.txt")
    prompt = prompt_template.format(today=today, text=text)

    try:
        completion = await client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "user", "content": prompt}],
            response_format=ExtractionResult,
            temperature=0.1,
        )

        logger.debug(
            "openai_response",
            model=completion.model,
            finish_reason=completion.choices[0].finish_reason,
            prompt_tokens=completion.usage.prompt_tokens if completion.usage else None,
            completion_tokens=completion.usage.completion_tokens if completion.usage else None,
            total_tokens=completion.usage.total_tokens if completion.usage else None,
        )

        extracted = completion.choices[0].message.parsed

        result = AnalyzeInteractionResponse(
            contact=extracted.contact,
            interaction=extracted.interaction,
            family_members=extracted.family_members,
            raw_text=text,
        )

        logger.info(
            "interaction_analyzed",
            contact_name=f"{result.contact.first_name} {result.contact.last_name}",
            family_members_count=len(result.family_members),
        )

        return result

    except Exception as e:
        logger.error("openai_error", error=str(e))
        raise
