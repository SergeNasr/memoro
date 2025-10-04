-- Get recent interactions for a contact (last 5)
SELECT id, user_id, contact_id, interaction_date, notes, location, created_at, updated_at
FROM interaction
WHERE contact_id = $1 AND user_id = $2
ORDER BY interaction_date DESC, created_at DESC
LIMIT 5;
