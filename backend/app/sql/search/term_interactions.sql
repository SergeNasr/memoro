-- Term-based search interactions (ILIKE matching)
SELECT
    i.id,
    i.contact_id,
    i.interaction_date,
    i.notes,
    i.location,
    c.first_name as contact_first_name,
    c.last_name as contact_last_name,
    1.0 as score  -- Term search doesn't provide relevance score
FROM interaction i
JOIN contact c ON i.contact_id = c.id
WHERE i.user_id = $1
    AND (
        i.notes ILIKE '%' || $2 || '%'
        OR i.location ILIKE '%' || $2 || '%'
    )
ORDER BY i.interaction_date DESC
LIMIT $3;
