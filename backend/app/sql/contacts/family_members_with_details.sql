-- Get family members with contact details
SELECT
    fm.id,
    fm.family_contact_id,
    fm.relationship,
    c.first_name,
    c.last_name
FROM family_member fm
JOIN contact c ON fm.family_contact_id = c.id
WHERE fm.contact_id = $1 AND c.user_id = $2
ORDER BY c.last_name, c.first_name;
