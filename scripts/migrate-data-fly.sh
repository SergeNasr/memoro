#!/usr/bin/env bash
set -euo pipefail

# Migrate local Memoro database to Fly Postgres
# Prerequisites: local Docker DB running, flyctl installed

APP_NAME="${1:-memoro}"
PG_APP="${APP_NAME}-db"
LOCAL_CONTAINER="memoro-postgres"
LOCAL_DB="memoro"
LOCAL_USER="memoro"
DUMP_FILE="/tmp/memoro-dump.sql"
PROXY_PORT=15432

echo "=== Migrate local DB to Fly Postgres ==="

# 1. Dump local database
echo "--- Dumping local database ---"
docker exec "$LOCAL_CONTAINER" pg_dump -U "$LOCAL_USER" -d "$LOCAL_DB" \
  --no-owner --no-privileges --clean --if-exists > "$DUMP_FILE"
echo "Dump saved to $DUMP_FILE ($(wc -c < "$DUMP_FILE") bytes)"

# 2. Open proxy tunnel in background
echo ""
echo "--- Opening proxy tunnel to Fly Postgres ---"
fly proxy "$PROXY_PORT:5432" --app "$PG_APP" &
PROXY_PID=$!
trap "kill $PROXY_PID 2>/dev/null || true; rm -f $DUMP_FILE" EXIT
sleep 3

# 3. Get connection info
echo "--- Getting Fly Postgres credentials ---"
echo "Enter the Fly Postgres connection string (from 'fly postgres connect' or dashboard):"
echo "Format: postgres://user:password@localhost:$PROXY_PORT/dbname"
read -rp "Connection string: " FLY_CONN

# Replace host:port with localhost proxy
FLY_CONN_LOCAL=$(echo "$FLY_CONN" | sed "s|@[^/]*|@localhost:$PROXY_PORT|")

# 4. Restore dump to Fly Postgres
echo ""
echo "--- Restoring dump to Fly Postgres ---"
psql "$FLY_CONN_LOCAL" < "$DUMP_FILE"

echo ""
echo "=== Migration complete! ==="
echo "Verify at: https://${APP_NAME}.fly.dev"
