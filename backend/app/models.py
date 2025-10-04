"""Pydantic models for request/response validation."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

# Interaction Analysis Models


class AnalyzeInteractionRequest(BaseModel):
    """Request model for analyzing interaction text."""

    text: str = Field(..., min_length=1, description="Raw interaction text to analyze")


class ExtractedContact(BaseModel):
    """Extracted contact information from interaction text."""

    first_name: str | None = Field(None, description="Contact's first name")
    last_name: str | None = Field(None, description="Contact's last name")
    birthday: date | None = Field(None, description="Contact's birthday if mentioned")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")


class ExtractedFamilyMember(BaseModel):
    """Extracted family member information."""

    first_name: str | None = Field(None, description="Family member's first name")
    last_name: str | None = Field(None, description="Family member's last name")
    relationship: str = Field(..., description="Relationship type (e.g., spouse, child, parent)")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")


class ExtractedInteraction(BaseModel):
    """Extracted interaction details."""

    notes: str = Field(..., description="Summary of interaction")
    location: str | None = Field(None, description="Location where interaction occurred")
    interaction_date: date = Field(..., description="Date of interaction")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score")


class AnalyzeInteractionResponse(BaseModel):
    """Response model for analyzed interaction."""

    contact: ExtractedContact
    interaction: ExtractedInteraction
    family_members: list[ExtractedFamilyMember] = Field(
        default_factory=list, description="Extracted family members"
    )
    raw_text: str = Field(..., description="Original input text")


class ConfirmInteractionRequest(BaseModel):
    """Request model for confirming and persisting interaction data."""

    contact: ExtractedContact
    interaction: ExtractedInteraction
    family_members: list[ExtractedFamilyMember] = Field(
        default_factory=list, description="Family members to link"
    )


class ConfirmInteractionResponse(BaseModel):
    """Response model for confirmed interaction."""

    contact_id: UUID = Field(..., description="ID of created/found contact")
    interaction_id: UUID = Field(..., description="ID of created interaction")
    family_members_linked: int = Field(..., description="Number of family members linked")


# Contact Models


class ContactBase(BaseModel):
    """Base contact fields."""

    first_name: str
    last_name: str
    birthday: date | None = None
    latest_news: str | None = None


class ContactCreate(ContactBase):
    """Contact creation request."""

    pass


class ContactUpdate(BaseModel):
    """Contact update request (all fields optional)."""

    first_name: str | None = None
    last_name: str | None = None
    birthday: date | None = None
    latest_news: str | None = None


class Contact(ContactBase):
    """Contact response model."""

    id: UUID
    user_id: UUID


class ContactListResponse(BaseModel):
    """Paginated contact list response."""

    contacts: list[Contact]
    total: int
    page: int
    page_size: int
    total_pages: int


# Interaction Models


class InteractionBase(BaseModel):
    """Base interaction fields."""

    contact_id: UUID
    interaction_date: date
    notes: str
    location: str | None = None


class InteractionCreate(InteractionBase):
    """Interaction creation request."""

    pass


class InteractionUpdate(BaseModel):
    """Interaction update request (all fields optional)."""

    interaction_date: date | None = None
    notes: str | None = None
    location: str | None = None


class Interaction(InteractionBase):
    """Interaction response model."""

    id: UUID
    user_id: UUID


# Family Member Models


class FamilyMemberCreate(BaseModel):
    """Family member creation request."""

    contact_id: UUID
    family_contact_id: UUID
    relationship: str


class FamilyMember(BaseModel):
    """Family member response model."""

    id: UUID
    contact_id: UUID
    family_contact_id: UUID
    relationship: str


class FamilyMemberWithDetails(BaseModel):
    """Family member with contact details."""

    id: UUID
    family_contact_id: UUID
    relationship: str
    first_name: str
    last_name: str


class ContactSummary(BaseModel):
    """Contact summary with statistics and recent activity."""

    contact: Contact
    total_interactions: int
    recent_interactions: list[Interaction]
    family_members: list[FamilyMemberWithDetails]
    last_interaction_date: date | None
