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
    ExtractedInteraction,
    ExtractedRelationship,
)

logger = structlog.get_logger(__name__)

client = AsyncOpenAI(api_key=settings.openai_api_key)


class ExtractionResult(BaseModel):
    """Structured extraction result for OpenAI API."""

    contact: ExtractedContact
    interaction: ExtractedInteraction
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


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
    """
    logger.info("analyzing_interaction", text_length=len(text))

    today = date.today().isoformat()
    prompt_template = load_prompt("extract_interaction.txt")
    prompt = prompt_template.format(today=today, text=text)

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
        relationships=extracted.relationships,
        raw_text=text,
    )

    logger.info(
        "interaction_analyzed",
        contact_name=f"{result.contact.first_name} {result.contact.last_name}",
        relationships_count=len(result.relationships),
    )

    return result


async def generate_embedding(text: str) -> list[float]:
    """
    Generate embedding vector for text using OpenAI API.

    Args:
        text: Text to generate embedding for

    Returns:
        Embedding vector as list of floats
    """
    logger.info("generating_embedding", text_length=len(text))

    response = await client.embeddings.create(
        model="text-embedding-3-small",
        input=text,
    )

    embedding = response.data[0].embedding

    logger.debug(
        "embedding_generated",
        embedding_dimensions=len(embedding),
        total_tokens=response.usage.total_tokens if response.usage else None,
    )

    return embedding


async def transcribe_audio(audio_file: bytes, filename: str) -> str:
    """
    Transcribe audio file using OpenAI Whisper API.

    Args:
        audio_file: Audio file bytes
        filename: Original filename (used to determine format)

    Returns:
        Transcribed text

    Raises:
        ValueError: If audio format is not supported
        Exception: If transcription fails
    """
    logger.info("transcribing_audio", filename=filename, file_size=len(audio_file))

    # Whisper supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
    supported_formats = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm"}
    file_ext = filename.lower().split(".")[-1] if "." in filename else ""

    if f".{file_ext}" not in supported_formats:
        raise ValueError(f"Unsupported audio format: {file_ext}. Supported: {supported_formats}")

    # OpenAI API accepts file-like objects
    from io import BytesIO

    audio_buffer = BytesIO(audio_file)
    audio_buffer.seek(0)  # Ensure we're at the start

    # Map file extensions to MIME types
    mime_types = {
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "mpeg": "audio/mpeg",
        "mpga": "audio/mpeg",
        "m4a": "audio/mp4",
        "wav": "audio/wav",
        "webm": "audio/webm",
    }
    mime_type = mime_types.get(file_ext, f"audio/{file_ext}")

    transcription = await client.audio.transcriptions.create(
        model="whisper-1",
        file=("audio." + file_ext, audio_buffer, mime_type),
    )

    text = transcription.text
    logger.info("audio_transcribed", text_length=len(text))
    return text
