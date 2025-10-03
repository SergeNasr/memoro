-- Count total contacts for a user
SELECT COUNT(*) as total
FROM contact
WHERE user_id = $1;
