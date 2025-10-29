-- Update a contact from UI form submission
-- Unlike the PATCH endpoint, this always updates all fields from the form
UPDATE contact
SET
    first_name = $3,
    last_name = NULLIF($4, ''),
    birthday = $5,
    latest_news = NULLIF($6, ''),
    updated_at = NOW()
WHERE id = $1 AND user_id = $2
RETURNING id, user_id, first_name, last_name, birthday, latest_news, created_at, updated_at;

