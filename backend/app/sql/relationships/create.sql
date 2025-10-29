-- Create relationship
-- Uses ON CONFLICT to avoid duplicate relationships
INSERT INTO relationship (contact_id, family_contact_id, relationship)
VALUES ($1, $2, $3)
ON CONFLICT ON CONSTRAINT uq_relationship_relationship DO NOTHING
RETURNING id, contact_id, family_contact_id, relationship;
