# Honeypot Collector Service

An asynchronous Python service that drains Redis lists and persists callback reports into a PostgreSQL (Supabase) database.

## Features
- **Efficient Ingestion:** Batch processing with `LPOP` and `executemany` for high throughput.
- **Robustness:** Built-in exponential backoff for database and Redis connectivity issues.
- **Idempotency:** Unique `report_id` constraint with `ON CONFLICT DO NOTHING` to prevent duplicates.
- **Graceful Shutdown:** Cleanly handles `SIGTERM` and `SIGINT` signals.
- **Health Monitoring:** Minimal JSON health endpoint on port 8080.
- **JSON Logging:** Structured logging for observability.

## Configuration (Environment Variables)

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379/0` |
| `FINAL_LIST` | Redis list for successful reports | `callbacks:final` |
| `DLQ_LIST` | Redis list for failed delivery reports (DLQ) | `callback:dlq` |
| `PG_DSN` | Postgres connection DSN (with SSL if needed) | `postgresql://user:pass@host:5432/db` |
| `BATCH_SIZE` | Maximum items to process per tick | `200` |
| `POLL_INTERVAL_MS` | Milliseconds to wait when list is empty | `500` |

## Run Instructions

### Using Docker (Recommended)
```bash
cd collector
docker build -t collector-service .
docker run -d 
  --env REDIS_URL="redis://your-redis-host:6379/0" 
  --env PG_DSN="postgresql://user:pass@your-pg-host:5432/db?sslmode=require" 
  -p 8080:8080 
  --name collector collector-service
```

### Locally
1. Install requirements:
   ```bash
   pip install -r collector/requirements.txt
   ```
2. Export environment variables:
   ```bash
   export REDIS_URL="redis://localhost:6379/0"
   export PG_DSN="postgresql://postgres:postgres@localhost:5432/postgres?sslmode=require"
   ```
3. Run the service:
   ```bash
   python collector/collector.py
   ```

## Database Tables
The service automatically initializes the following schema on startup:

- **`callbacks`**: Primary table for successful honeypot reports.
- **`callbacks_dlq`**: Table for reports that failed all delivery attempts.

**Fields extracted from payload:**
- `report_id`: Unique identifier (UUID or SessionID:Fingerprint).
- `session_id`: Unique session identifier.
- `scam_detected`: Boolean flag from the detector.
- `scam_type`: Classified scam category.
- `confidence_level`: Detector confidence (0.0 - 1.0).
- `total_messages`: Number of messages in the conversation.
- `engagement_duration`: Duration in seconds.
- `channel`: Metadata channel (SMS, WhatsApp, etc).
- `payload`: Full JSON report for historical reference.
