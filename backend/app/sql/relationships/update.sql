-- Update relationship
UPDATE relationship
SET relationship = $4, updated_at = now()
WHERE id = $1 AND contact_id IN (SELECT id FROM contact WHERE user_id = $2)
RETURNING id, contact_id, family_contact_id, relationship;

