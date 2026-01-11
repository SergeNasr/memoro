"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

from backend.app.services.llm import generate_embedding


class TestEmbeddings:
    """Embedding generation tests."""

    async def test_generate_embedding(self):
        """Generate embedding returns vector."""
        mock_embedding = [0.1] * 1536

        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=mock_embedding)]
        mock_response.usage = MagicMock(total_tokens=10)

        with patch("backend.app.services.llm.client") as mock_client:
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)
            result = await generate_embedding("Test interaction notes")

            assert result == mock_embedding
            mock_client.embeddings.create.assert_called_once_with(
                model="text-embedding-3-small", input="Test interaction notes"
            )
