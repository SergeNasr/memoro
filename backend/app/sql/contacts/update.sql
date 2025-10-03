-- Update a contact's details
UPDATE contact
SET
    first_name = COALESCE($3, first_name),
    last_name = COALESCE($4, last_name),
    birthday = COALESCE($5, birthday),
    latest_news = COALESCE($6, latest_news),
    updated_at = NOW()
WHERE id = $1 AND user_id = $2
RETURNING id, user_id, first_name, last_name, birthday, latest_news, created_at, updated_at;
