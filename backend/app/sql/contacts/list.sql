-- List contacts for a user with pagination
SELECT
    id,
    first_name,
    last_name,
    birthday,
    latest_news,
    created_at,
    updated_at
FROM contact
WHERE user_id = $1
ORDER BY last_name ASC, first_name ASC
LIMIT $2
OFFSET $3;
