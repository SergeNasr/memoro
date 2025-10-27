"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.llm import generate_embedding


class TestGenerateEmbedding:
    """Tests for generate_embedding function."""

    @pytest.mark.asyncio
    async def test_generate_embedding_success(self):
        """Test successful embedding generation."""
        mock_embedding = [
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
        ] * 307  # 1536 dimensions for text-embedding-3-small

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.usage = MagicMock(total_tokens=10)

        with patch("backend.app.services.llm.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding("Test interaction notes")

            assert result == mock_embedding
            assert len(result) == 1535
            mock_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small",
                input="Test interaction notes",
            )

    @pytest.mark.asyncio
    async def test_generate_embedding_with_long_text(self):
        """Test embedding generation with longer text."""
        long_text = "This is a long interaction note. " * 100
        mock_embedding = [0.5] * 1536

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.usage = MagicMock(total_tokens=500)

        with patch("backend.app.services.llm.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding(long_text)

            assert result == mock_embedding
            assert len(result) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_empty_text(self):
        """Test embedding generation with empty text."""
        mock_embedding = [0.0] * 1536

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.usage = MagicMock(total_tokens=1)

        with patch("backend.app.services.llm.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding("")

            assert result == mock_embedding

    @pytest.mark.asyncio
    async def test_generate_embedding_special_characters(self):
        """Test embedding generation with special characters."""
        text_with_special = "Meeting at café 🎉 with notes: $100 budget"
        mock_embedding = [0.3] * 1536

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.usage = MagicMock(total_tokens=15)

        with patch("backend.app.services.llm.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            result = await generate_embedding(text_with_special)

            assert result == mock_embedding
            mock_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small",
                input=text_with_special,
            )
