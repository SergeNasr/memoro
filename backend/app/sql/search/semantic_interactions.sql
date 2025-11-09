-- Semantic search interactions using pgvector cosine similarity
SELECT
    i.id,
    i.contact_id,
    i.interaction_date,
    i.notes,
    i.location,
    c.first_name,
    c.last_name,
    c.birthday,
    c.latest_news,
    1 - (i.embedding <=> $2::vector) as score
FROM interaction i
JOIN contact c ON i.contact_id = c.id
WHERE i.user_id = $1
    AND i.embedding IS NOT NULL
ORDER BY i.embedding <=> $2::vector
LIMIT $3;
