-- Find existing contact or create new one
-- If contact exists (by name and user_id), return it; otherwise create new contact
WITH existing AS (
    SELECT id, first_name, last_name, birthday, latest_news, user_id
    FROM contact
    WHERE user_id = $1
      AND LOWER(first_name) = LOWER($2)
      AND LOWER(last_name) = LOWER($3)
    LIMIT 1
),
inserted AS (
    INSERT INTO contact (user_id, first_name, last_name, birthday, latest_news)
    SELECT $1, $2, $3, $4, $5
    WHERE NOT EXISTS (SELECT 1 FROM existing)
    RETURNING id, first_name, last_name, birthday, latest_news, user_id
)
SELECT id, first_name, last_name, birthday, latest_news, user_id
FROM existing
UNION ALL
SELECT id, first_name, last_name, birthday, latest_news, user_id
FROM inserted;
