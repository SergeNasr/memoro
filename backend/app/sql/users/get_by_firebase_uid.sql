-- Get user by Firebase UID
SELECT id FROM "user" WHERE firebase_uid = $1;
