-- Get or create user by Firebase UID
-- First try to insert, on conflict do nothing
-- Then select the user (either existing or newly created)
INSERT INTO "user" (firebase_uid, email, first_name, last_name)
VALUES ($1, $2, '', '')
ON CONFLICT (firebase_uid) DO NOTHING;

SELECT id FROM "user" WHERE firebase_uid = $1;
