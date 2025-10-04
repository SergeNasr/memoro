-- Delete an interaction (returns deleted row if successful)
DELETE FROM interaction
WHERE id = $1 AND user_id = $2
RETURNING id;
