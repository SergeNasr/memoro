-- Create new interaction
INSERT INTO interaction (user_id, contact_id, interaction_date, notes, location, embedding)
VALUES ($1, $2, $3, $4, $5, $6)
RETURNING id, user_id, contact_id, interaction_date, notes, location, created_at, updated_at;
