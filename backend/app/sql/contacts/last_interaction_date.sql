-- Get the date of the most recent interaction for a contact
SELECT MAX(interaction_date) as last_interaction_date
FROM interaction
WHERE contact_id = $1 AND user_id = $2;
