-- Get relationships with contact details
SELECT
    r.id,
    r.family_contact_id,
    r.relationship,
    c.first_name,
    c.last_name
FROM relationship r
JOIN contact c ON r.family_contact_id = c.id
WHERE r.contact_id = $1 AND c.user_id = $2
ORDER BY c.last_name, c.first_name;
