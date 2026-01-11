"""Tests for UI endpoints (HTMX fragments)."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from httpx import AsyncClient

from backend.app.models import ExtractedContact, ExtractedInteraction
from backend.tests.conftest import make_openai_completion


class TestInteractionUI:
    """UI endpoints for interactions."""

    async def test_analyze_form(self, client: AsyncClient, mock_openai_client, mock_db_connection):
        """Analyze via form returns HTML review form."""
        mock_completion = make_openai_completion(
            contact=ExtractedContact(
                first_name="Sarah", last_name="Johnson", birthday=None, confidence=0.95
            ),
            interaction=ExtractedInteraction(
                notes="Coffee at Starbucks",
                location="Starbucks",
                interaction_date=date(2025, 10, 15),
                confidence=0.9,
            ),
            relationships=[],
        )
        mock_openai_client.beta.chat.completions.parse = AsyncMock(return_value=mock_completion)

        response = await client.post(
            "/ui/interactions/analyze", data={"text": "Had coffee with Sarah"}
        )
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"Sarah" in response.content

    async def test_confirm_redirects(
        self, client: AsyncClient, mock_db_transaction, mock_openai_client
    ):
        """Confirm redirects to contact profile."""
        contact_id, interaction_id = uuid4(), uuid4()

        def mock_fetchrow(*args, **kwargs):
            query = str(args[0]).lower()
            if "interaction" in query and "insert" in query:
                return mock_db_transaction.make_record(
                    id=interaction_id,
                    user_id=UUID("00000000-0000-0000-0000-000000000000"),
                    contact_id=contact_id,
                    interaction_date=date(2025, 10, 15),
                    notes="Coffee",
                    location="Starbucks",
                    created_at=None,
                    updated_at=None,
                )
            return mock_db_transaction.make_record(
                id=contact_id,
                first_name="Sarah",
                last_name="Johnson",
                birthday=None,
                latest_news="Coffee",
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
            )

        mock_db_transaction.fetchrow.side_effect = mock_fetchrow

        response = await client.post(
            "/ui/interactions/confirm",
            data={
                "contact.first_name": "Sarah",
                "contact.last_name": "Johnson",
                "interaction.interaction_date": "2025-10-15",
                "interaction.notes": "Coffee",
                "interaction.location": "Starbucks",
            },
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert response.headers["location"] == f"/contacts/{contact_id}"

    async def test_get_fragment(self, client: AsyncClient, mock_db_connection):
        """Get interaction fragment returns HTML."""
        interaction_id, contact_id = uuid4(), uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Coffee",
            location="Starbucks",
        )

        response = await client.get(f"/ui/interactions/{interaction_id}")
        assert response.status_code == 200
        assert b"Coffee" in response.content
        assert b"[edit]" in response.content

    async def test_edit_form(self, client: AsyncClient, mock_db_connection):
        """Get edit form returns HTML form."""
        interaction_id, contact_id = uuid4(), uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(
            id=interaction_id,
            user_id=UUID("00000000-0000-0000-0000-000000000000"),
            contact_id=contact_id,
            interaction_date=date(2024, 1, 15),
            notes="Coffee",
            location="Starbucks",
        )

        response = await client.get(f"/ui/interactions/{interaction_id}/edit")
        assert response.status_code == 200
        assert b"Save" in response.content
        assert b"Cancel" in response.content


class TestContactUI:
    """UI endpoints for contacts."""

    async def test_header(self, client: AsyncClient, mock_db_connection):
        """Get contact header fragment."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Sarah",
                last_name="Johnson",
                birthday=date(1990, 5, 15),
                latest_news="News",
            ),
            mock_db_connection.make_record(total=5),
            mock_db_connection.make_record(last_interaction_date=date(2024, 1, 15)),
        ]
        mock_db_connection.fetch.side_effect = [[], []]

        response = await client.get(f"/ui/contacts/{contact_id}/header")
        assert response.status_code == 200
        assert b"Sarah" in response.content
        assert b"[edit]" in response.content

    async def test_delete_modal(self, client: AsyncClient, mock_db_connection):
        """Get delete confirmation modal."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.side_effect = [
            mock_db_connection.make_record(
                id=contact_id,
                user_id=UUID("00000000-0000-0000-0000-000000000000"),
                first_name="Sarah",
                last_name="Johnson",
                birthday=None,
                latest_news=None,
            ),
            mock_db_connection.make_record(total=5),
            mock_db_connection.make_record(last_interaction_date=date(2024, 1, 15)),
        ]
        mock_db_connection.fetch.side_effect = [[], []]

        response = await client.get(f"/ui/contacts/{contact_id}/delete")
        assert response.status_code == 200
        assert b"Delete Contact" in response.content
        assert b"cannot be undone" in response.content

    async def test_delete(self, client: AsyncClient, mock_db_connection):
        """Delete contact via UI redirects to home."""
        contact_id = uuid4()
        mock_db_connection.fetchrow.return_value = mock_db_connection.make_record(id=contact_id)

        response = await client.delete(f"/ui/contacts/{contact_id}")
        assert response.status_code == 200
        assert response.headers["HX-Redirect"] == "/"


class TestTranscribe:
    """Audio transcription UI."""

    async def test_transcribe(self, client: AsyncClient, mock_openai_client):
        """Transcribe audio returns text."""
        mock_transcription = MagicMock()
        mock_transcription.text = "Had coffee with Sarah"
        mock_openai_client.audio.transcriptions.create = AsyncMock(return_value=mock_transcription)

        response = await client.post(
            "/ui/interactions/transcribe",
            files={"audio": ("recording.webm", b"fake audio data", "audio/webm")},
        )
        assert response.status_code == 200
        assert response.json()["text"] == "Had coffee with Sarah"
