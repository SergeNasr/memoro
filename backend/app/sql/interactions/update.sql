-- Update an interaction's details
UPDATE interaction
SET
    notes = COALESCE($3, notes),
    location = COALESCE($4, location),
    interaction_date = COALESCE($5, interaction_date),
    updated_at = NOW()
WHERE id = $1 AND user_id = $2
RETURNING id, user_id, contact_id, interaction_date, notes, location, created_at, updated_at;
