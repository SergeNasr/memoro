-- Get or create user by Firebase UID
-- Uses DO UPDATE (no-op) to enable RETURNING on conflict
INSERT INTO "user" (firebase_uid, email, first_name, last_name)
VALUES ($1, $2, '', '')
ON CONFLICT (firebase_uid) DO UPDATE SET firebase_uid = EXCLUDED.firebase_uid
RETURNING id;
