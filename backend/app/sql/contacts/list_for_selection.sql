-- List contacts for selection (excluding a specific contact)
SELECT id, first_name, last_name, birthday
FROM contact
WHERE user_id = $1 AND id != $2
ORDER BY last_name, first_name
LIMIT 100;

