-- Count total interactions for a contact
SELECT COUNT(*) as total
FROM interaction
WHERE contact_id = $1 AND user_id = $2;
