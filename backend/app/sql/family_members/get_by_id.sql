-- Get family member relationship by ID
SELECT
    fm.id,
    fm.contact_id,
    fm.family_contact_id,
    fm.relationship
FROM family_member fm
JOIN contact c ON fm.contact_id = c.id
WHERE fm.id = $1 AND c.user_id = $2;

