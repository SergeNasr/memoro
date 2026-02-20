#!/usr/bin/env bash
set -euo pipefail

# Memoro — Fly.io one-time setup
# Prerequisites: brew install flyctl && fly auth login

APP_NAME="${1:-memoro}"
REGION="${2:-iad}"
PG_APP="${APP_NAME}-db"

echo "=== Memoro Fly.io Setup ==="
echo "App name: $APP_NAME"
echo "Region:   $REGION"
echo ""

# 1. Create Fly app
echo "--- Creating Fly app ---"
fly apps create "$APP_NAME" --machines || echo "App may already exist, continuing..."

# 2. Create Fly Postgres
echo ""
echo "--- Creating Fly Postgres ($PG_APP) ---"
fly postgres create \
  --name "$PG_APP" \
  --region "$REGION" \
  --vm-size shared-cpu-1x \
  --initial-cluster-size 1 \
  --volume-size 1 || echo "Postgres app may already exist, continuing..."

# 3. Ensure Postgres machine is running before attach
echo ""
echo "--- Ensuring Postgres is running ---"
PG_MACHINE_ID=$(fly machine list --app "$PG_APP" --json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['id'])" 2>/dev/null || true)

if [ -n "$PG_MACHINE_ID" ]; then
  PG_STATE=$(fly machine list --app "$PG_APP" --json | python3 -c "import sys,json; print(json.load(sys.stdin)[0]['state'])" 2>/dev/null || true)
  if [ "$PG_STATE" != "started" ]; then
    echo "Postgres machine is $PG_STATE, starting it..."
    fly machine start "$PG_MACHINE_ID" --app "$PG_APP"
    echo "Waiting for Postgres to become ready..."
    sleep 10
  fi

  # Wait for leader election (checks passing)
  echo "Waiting for Postgres leader election..."
  for i in {1..12}; do
    ROLE=$(fly machine list --app "$PG_APP" --json | python3 -c "import sys,json; m=json.load(sys.stdin)[0]; print(m.get('config',{}).get('metadata',{}).get('role',''))" 2>/dev/null || true)
    if [ "$ROLE" = "primary" ]; then
      echo "Postgres is ready (role: primary)"
      break
    fi
    echo "  Attempt $i/12 — waiting 5s..."
    sleep 5
  done
else
  echo "Error: No Postgres machine found in $PG_APP"
  exit 1
fi

# 4. Attach Postgres (auto-sets DATABASE_URL secret)
echo ""
echo "--- Attaching Postgres to app ---"
fly postgres attach "$PG_APP" --app "$APP_NAME" || echo "Already attached, continuing..."

# 5. Verify DATABASE_URL is set
echo ""
echo "--- Verifying DATABASE_URL ---"
if fly secrets list --app "$APP_NAME" | grep -q "DATABASE_URL"; then
  echo "DATABASE_URL is set."
else
  echo "Error: DATABASE_URL was not set by postgres attach."
  echo "Try manually: fly postgres attach $PG_APP --app $APP_NAME"
  exit 1
fi

# 6. Set secrets
echo ""
echo "--- Setting secrets ---"

read -rp "OPENAI_API_KEY: " OPENAI_API_KEY
read -rp "SECRET_KEY (leave blank to generate): " SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
  SECRET_KEY=$(openssl rand -hex 32)
  echo "Generated SECRET_KEY: $SECRET_KEY"
fi
read -rp "FIREBASE_PROJECT_ID: " FIREBASE_PROJECT_ID
read -rp "FIREBASE_WEB_API_KEY: " FIREBASE_WEB_API_KEY
read -rp "Path to Firebase service account JSON file: " SA_PATH

if [ ! -f "$SA_PATH" ]; then
  echo "Error: File not found: $SA_PATH"
  exit 1
fi
FIREBASE_SERVICE_ACCOUNT_JSON=$(cat "$SA_PATH")

fly secrets set \
  --app "$APP_NAME" \
  OPENAI_API_KEY="$OPENAI_API_KEY" \
  SECRET_KEY="$SECRET_KEY" \
  FIREBASE_PROJECT_ID="$FIREBASE_PROJECT_ID" \
  FIREBASE_WEB_API_KEY="$FIREBASE_WEB_API_KEY" \
  FIREBASE_SERVICE_ACCOUNT_JSON="$FIREBASE_SERVICE_ACCOUNT_JSON"

# 7. Deploy
echo ""
echo "--- Deploying ---"
fly deploy --app "$APP_NAME"

# 8. Run migrations
echo ""
echo "--- Running database migrations ---"
fly ssh console --app "$APP_NAME" -C "uv run alembic upgrade head"

# 9. Health check
echo ""
echo "--- Health check ---"
sleep 5
curl -sf "https://${APP_NAME}.fly.dev/health" && echo "" && echo "Health check passed!" || echo "Health check failed — app may still be starting."

echo ""
echo "=== Setup complete! ==="
echo "Visit: https://${APP_NAME}.fly.dev"
