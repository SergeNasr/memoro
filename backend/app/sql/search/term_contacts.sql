-- Term-based search contacts (ILIKE matching)
SELECT
    id,
    first_name,
    last_name,
    birthday,
    latest_news,
    1.0 as score  -- Term search doesn't provide relevance score
FROM contact
WHERE user_id = $1
    AND (
        first_name ILIKE '%' || $2 || '%'
        OR last_name ILIKE '%' || $2 || '%'
        OR latest_news ILIKE '%' || $2 || '%'
    )
ORDER BY first_name, last_name
LIMIT $3;
