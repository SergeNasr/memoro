-- Soft delete a contact (returns deleted row if successful)
DELETE FROM contact
WHERE id = $1 AND user_id = $2
RETURNING id;
