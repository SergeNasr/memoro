# Scripts

Ad-hoc utility scripts for maintenance and data operations.

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

