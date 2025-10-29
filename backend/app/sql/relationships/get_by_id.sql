-- Get relationship by ID
SELECT
    r.id,
    r.contact_id,
    r.family_contact_id,
    r.relationship
FROM relationship r
JOIN contact c ON r.contact_id = c.id
WHERE r.id = $1 AND c.user_id = $2;

