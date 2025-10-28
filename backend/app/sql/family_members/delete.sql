-- Delete family member relationship
DELETE FROM family_member
WHERE id = $1 AND contact_id IN (SELECT id FROM contact WHERE user_id = $2)
RETURNING id;

