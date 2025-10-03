-- Get a single contact by ID
SELECT
    id,
    user_id,
    first_name,
    last_name,
    birthday,
    latest_news,
    created_at,
    updated_at
FROM contact
WHERE id = $1 AND user_id = $2;
