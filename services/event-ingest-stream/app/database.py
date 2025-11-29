import redis.asyncio as redis
import asyncpg
import os
import json
from .models import AnomalyReport, IngestEvent

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN")
if not POSTGRES_DSN:
    # Fallback only if strictly necessary, but better to fail if not set in prod.
    # For local dev without env, we can warn.
    print("WARNING: POSTGRES_DSN not set. Database connection will fail.")

async def get_redis():
    """Returns a Redis connection."""
    return await redis.from_url(f"redis://{REDIS_HOST}")

async def create_postgres_pool():
    """Creates a connection pool on startup."""
    print("Creating PostgreSQL connection pool...")
    return await asyncpg.create_pool(POSTGRES_DSN, min_size=5, max_size=20)

async def get_postgres_conn(pool: asyncpg.Pool):
    """
    Dependency to get a connection from the pool.
    This will be managed by FastAPI.
    """
    if pool is None:
        raise Exception("Postgres pool is not initialized")
    
    async with pool.acquire() as connection:
        yield connection

# --- Core Logic ---

async def add_event_to_stream(event: IngestEvent, r: redis.Redis):
    """
    Asynchronously adds a validated event to the Redis Stream.
    """
    event_data = event.model_dump_json()
    # Using 'event:raw' as the stream name
    await r.xadd("events:raw", {"data": event_data})

async def log_anomaly_to_db(anomaly: AnomalyReport, conn: asyncpg.Connection):
    """
    Asynchronously logs a detected anomaly to the secure Postgres audit log.
    """
    # This demonstrates secure, parameterized queries. No SQL injection.
    await conn.execute(
        """
        INSERT INTO anomalies (source_ip, score, event_type, timestamp, details)
        VALUES ($1, $2, $3, $4, $5)
        """,
        str(anomaly.source_ip),
        anomaly.score,
        anomaly.event_type,
        anomaly.timestamp,
        json.dumps(anomaly.details),
    )

async def fetch_anomalies_from_db(conn: asyncpg.Connection):
    """
    Fetches the latest anomalies for the Streamlit dashboard.
    """
    rows = await conn.fetch("SELECT * FROM anomalies ORDER BY timestamp DESC LIMIT 100")
    return [dict(row) for row in rows]