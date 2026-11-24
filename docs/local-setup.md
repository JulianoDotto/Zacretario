# Local setup

## Docker (test database)

Database tests run against Postgres in Docker. Start it from the project root:

```bash
docker compose up -d db
```

Then point the tests at it:

```bash
export TEST_DATABASE_URL=postgresql+psycopg://zacretario:zacretario@localhost:5433/zacretario_test
uv run pytest
```

Without `TEST_DATABASE_URL`, tests fall back to in-memory SQLite.

## Neon (database)

TODO: filled in Task 12

## Google Cloud (Calendar)

TODO: filled in Task 12

## Meta / WhatsApp

TODO: filled in Task 12

## Running locally with a tunnel

TODO: filled in Task 12

## Domain & DNS

TODO: filled in Task 12
