# Scripts

Ad-hoc utility scripts for maintenance, deployment, and data operations.

## Fly.io Setup

One-time interactive setup for deploying Memoro to Fly.io.

**What it does:**
1. Creates Fly app and Postgres database
2. Ensures Postgres is running and ready (handles cold starts)
3. Attaches Postgres (sets `DATABASE_URL` secret)
4. Verifies `DATABASE_URL` was set before proceeding
5. Prompts for secrets (OpenAI, Firebase, etc.)
6. Deploys the app and runs migrations

**Usage:**
```bash
# Prerequisites: brew install flyctl && fly auth login
./scripts/setup-fly.sh              # defaults to app name "memoro"
./scripts/setup-fly.sh myapp iad    # custom app name and region
```

## Migrate Data to Fly

Migrates your local Docker Postgres database to Fly Postgres.

**Usage:**
```bash
./scripts/migrate-data-fly.sh          # defaults to app "memoro"
./scripts/migrate-data-fly.sh myapp    # custom app name
```

**Requirements:**
- Local Docker database running (`docker-compose up -d`)
- Fly Postgres connection string (from Fly dashboard)

## Backfill Embeddings

Generates embeddings for interactions that are missing them.

**Safety features:**
- Maximum 20 interactions per run (prevent accidental large bills)
- Requires manual confirmation before proceeding
- Shows estimated cost

**Usage:**
```bash
just backfill-embeddings
```

**Requirements:**
- `DATABASE_URL` environment variable set
- `OPENAI_API_KEY` environment variable set
- Database must be running and migrated

**Cost estimate:**
- ~$0.01 USD per 100 interactions
- Uses `text-embedding-3-small` model

## Import Contacts from TSV

Import contacts and relationships from a TSV (tab-separated values) file into Memoro.

**TSV Format:**
Tab-separated values with the following columns:
- `Name` - Full name of the person (required)
- `Related to (person) / Relationship` - Format: "Person Name / Relationship" (e.g., "Drew / Girlfriend")
- `Place` - Location where you met them
- `Description` - Additional notes about the person

**Features:**
- Preview mode by default (safe, no changes)
- Automatically finds or creates contacts (avoids duplicates)
- Creates interactions with embeddings for each person
- Links family relationships bidirectionally
- If person A is related to person B, creates person B first
- All TSV/CSV files are ignored by git (contains personal data)

**Usage:**
```bash
# Preview what will be imported (default, no changes, no OpenAI calls)
just import path/to/contacts.tsv

# Actually import the contacts (makes DB changes, calls OpenAI)
just import-execute path/to/contacts.tsv

# Or run directly with Python
python scripts/import_tsv.py path/to/contacts.tsv           # preview
python scripts/import_tsv.py --execute path/to/contacts.tsv  # execute
```

**Example TSV:**
```
Name	Related to (person) / Relationship	Place	Description
Michael		Cecily	Bartender
Allie	Drew / Girlfriend	Million Goods	
Caspian	Kimia Hamidi / Son	Ramp	
```

**Requirements:**
- TSV file must be tab-separated (standard format for Excel/Google Sheets exports)
- `DATABASE_URL` environment variable set
- `OPENAI_API_KEY` environment variable set (only for execute mode)

**Rollback:**
If you need to undo an import, you can rollback using the same TSV file:

```bash
# Preview what will be deleted
just import-rollback path/to/contacts.tsv

# Actually delete the contacts (DESTRUCTIVE!)
just import-rollback-execute path/to/contacts.tsv

# Or run directly with Python
python scripts/rollback_import.py path/to/contacts.tsv           # preview
python scripts/rollback_import.py --execute path/to/contacts.tsv  # execute
```

⚠️ **Warning**: Rollback deletes contacts and all associated interactions and family relationships!

