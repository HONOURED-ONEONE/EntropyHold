import asyncio
import json
import logging
import os
import signal
import sys
import time
from typing import Any, Dict, List, Optional

import asyncpg
import redis.asyncio as redis
from aiohttp import web
from pythonjsonlogger import jsonlogger


# Configure JSON logging
log_handler = logging.StreamHandler(sys.stdout)
formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(message)s")
log_handler.setFormatter(formatter)
logger = logging.getLogger("collector")
logger.addHandler(log_handler)
logger.setLevel(logging.INFO)


# ENV configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FINAL_LIST = os.getenv("FINAL_LIST", "callbacks:final")
DLQ_LIST = os.getenv("DLQ_LIST", "callback:dlq")
PG_DSN = os.getenv("PG_DSN", "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=require")
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "200"))
POLL_INTERVAL_MS = int(os.getenv("POLL_INTERVAL_MS", "500"))


# Shared shutdown event
shutdown_event = asyncio.Event()


def extract_data(raw_item: str) -> Optional[Dict[str, Any]]:
    """
    Parses raw list item and extracts required fields for the database.
    Handles both direct report payloads and DLQ-wrapped payloads.
    """
    try:
        item = json.loads(raw_item)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON", extra={"raw": raw_item[:100]})
        return None

    # Handle DLQ wrapping (finalReport key)
    if "finalReport" in item:
        payload = item["finalReport"]
    else:
        payload = item

    session_id = payload.get("sessionId")
    scam_detected = payload.get("scamDetected")
    scam_type = payload.get("scamType")
    confidence_level = payload.get("confidenceLevel")
    total_messages = payload.get("totalMessagesExchanged")
    engagement_duration = payload.get("engagementDurationSeconds")

    # Metadata extraction
    metadata = payload.get("metadata") or {}
    channel = metadata.get("channel") or payload.get("channel")

    # report_id logic
    intel = payload.get("extractedIntelligence") or {}
    meta = intel.get("_meta") or {}
    report_id = meta.get("reportId")
    if not report_id:
        fingerprint = meta.get("payloadFingerprint")
        report_id = f"{session_id}:{fingerprint}"

    return {
        "report_id": str(report_id),
        "session_id": str(session_id),
        "scam_detected": bool(scam_detected) if scam_detected is not None else None,
        "scam_type": str(scam_type) if scam_type else None,
        "confidence_level": float(confidence_level) if confidence_level is not None else None,
        "total_messages": int(total_messages) if total_messages is not None else None,
        "engagement_duration": int(engagement_duration) if engagement_duration is not None else None,
        "channel": str(channel) if channel else None,
        "payload": json.dumps(payload),
    }


async def process_batch(pool: asyncpg.Pool, items: List[str], table: str):
    """
    Extracts data from batch of raw items and inserts into specified table.
    Uses ON CONFLICT DO NOTHING to ensure idempotency via report_id.
    """
    extracted_items = []
    for raw in items:
        data = extract_data(raw)
        if data:
            extracted_items.append((
                data["report_id"], data["session_id"], data["scam_detected"],
                data["scam_type"], data["confidence_level"], data["total_messages"],
                data["engagement_duration"], data["channel"], data["payload"]
            ))

    if not extracted_items:
        return

    query = f"""
        INSERT INTO {table} (
            report_id, session_id, scam_detected, scam_type, confidence_level,
            total_messages, engagement_duration, channel, payload
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (report_id) DO NOTHING;
    """
    
    await pool.executemany(query, extracted_items)
    logger.info(f"Inserted batch into {table}", extra={"count": len(extracted_items)})


async def drain_list(redis_conn: redis.Redis, pool: asyncpg.Pool, list_name: str, table_name: str):
    """
    Continuous loop draining a Redis list and processing items in batches.
    Includes exponential backoff for connection/database errors.
    """
    logger.info(f"Starting drain task: {list_name} -> {table_name}")
    backoff = 1
    while not shutdown_event.is_set():
        try:
            # redis-py 5.0+ supports count parameter for lpop
            items = await redis_conn.lpop(list_name, count=BATCH_SIZE)
            if items:
                # Ensure items is a list (lpop with count returns list)
                if isinstance(items, str):
                    items = [items]
                await process_batch(pool, items, table_name)
                backoff = 1  # Reset backoff on success
            else:
                await asyncio.sleep(POLL_INTERVAL_MS / 1000.0)
        except Exception as e:
            logger.error(f"Error in drain loop for {list_name}", extra={"error": str(e), "backoff": backoff})
            await asyncio.sleep(min(backoff, 60))
            backoff *= 2


async def init_db(pool: asyncpg.Pool):
    """Ensures required tables exist on startup."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS callbacks (
                report_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                scam_detected BOOLEAN,
                scam_type TEXT,
                confidence_level DOUBLE PRECISION,
                total_messages INTEGER,
                engagement_duration INTEGER,
                channel TEXT,
                payload JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_callbacks_session ON callbacks(session_id);

            CREATE TABLE IF NOT EXISTS callbacks_dlq (
                report_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                scam_detected BOOLEAN,
                scam_type TEXT,
                confidence_level DOUBLE PRECISION,
                total_messages INTEGER,
                engagement_duration INTEGER,
                channel TEXT,
                payload JSONB,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_callbacks_dlq_session ON callbacks_dlq(session_id);
        """)
    logger.info("Database initialized (tables verified)")


async def health_check_handler(request):
    return web.json_response({"status": "ok"})


async def run_health_server():
    """Minimal health check server on port 8080."""
    app = web.Application()
    app.router.add_get("/", health_check_handler)
    app.router.add_get("/health", health_check_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    logger.info("Health server listening on port 8080")
    try:
        await shutdown_event.wait()
    finally:
        await runner.cleanup()


async def main():
    # Signal handling
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, shutdown_event.set)

    logger.info("Initializing collector service")
    
    # Connect to Postgres with retry
    pool = None
    while not shutdown_event.is_set():
        try:
            pool = await asyncpg.create_pool(PG_DSN, min_size=1, max_size=10)
            await init_db(pool)
            break
        except Exception as e:
            logger.error("Failed to connect to Postgres, retrying...", extra={"error": str(e)})
            await asyncio.sleep(5)
    
    if not pool:
        return

    # Connect to Redis with retry
    redis_conn = None
    while not shutdown_event.is_set():
        try:
            redis_conn = redis.from_url(REDIS_URL, decode_responses=True)
            await redis_conn.ping()
            logger.info("Connected to Redis")
            break
        except Exception as e:
            logger.error("Failed to connect to Redis, retrying...", extra={"error": str(e)})
            await asyncio.sleep(5)
    
    if not redis_conn:
        await pool.close()
        return

    try:
        # Run tasks concurrently
        await asyncio.gather(
            drain_list(redis_conn, pool, FINAL_LIST, "callbacks"),
            drain_list(redis_conn, pool, DLQ_LIST, "callbacks_dlq"),
            run_health_server()
        )
    finally:
        logger.info("Shutting down collector service")
        await redis_conn.close()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
