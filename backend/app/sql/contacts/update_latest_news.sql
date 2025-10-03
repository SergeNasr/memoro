-- Update contact's latest_news field
UPDATE contact
SET latest_news = $2,
    updated_at = now()
WHERE id = $1
RETURNING id, first_name, last_name, birthday, latest_news, user_id;
