-- Create family member relationship
-- Uses ON CONFLICT to avoid duplicate relationships
INSERT INTO family_member (contact_id, family_contact_id, relationship)
VALUES ($1, $2, $3)
ON CONFLICT ON CONSTRAINT uq_family_member_relationship DO NOTHING
RETURNING id, contact_id, family_contact_id, relationship;
