-- Fuzzy search contacts by name
SELECT
    id,
    first_name,
    last_name,
    birthday,
    latest_news,
    SIMILARITY(first_name || ' ' || last_name, $2) as score
FROM contact
WHERE user_id = $1
    AND (first_name % $2 OR last_name % $2 OR (first_name || ' ' || last_name) % $2)
ORDER BY score DESC
LIMIT $3;
