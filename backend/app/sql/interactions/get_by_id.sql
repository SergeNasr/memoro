-- Get a single interaction by ID
SELECT
    id,
    user_id,
    contact_id,
    interaction_date,
    notes,
    location,
    created_at,
    updated_at
FROM interaction
WHERE id = $1 AND user_id = $2;
