-- Fuzzy search interactions by notes or location
SELECT
    i.id,
    i.contact_id,
    i.interaction_date,
    i.notes,
    i.location,
    c.first_name as contact_first_name,
    c.last_name as contact_last_name,
    GREATEST(
        SIMILARITY(i.notes, $2),
        COALESCE(SIMILARITY(i.location, $2), 0)
    ) as score
FROM interaction i
JOIN contact c ON i.contact_id = c.id
WHERE i.user_id = $1
    AND (i.notes % $2 OR i.location % $2)
ORDER BY score DESC
LIMIT $3;
