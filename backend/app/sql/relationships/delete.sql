-- Delete relationship
DELETE FROM relationship
WHERE id = $1 AND contact_id IN (SELECT id FROM contact WHERE user_id = $2)
RETURNING id;

