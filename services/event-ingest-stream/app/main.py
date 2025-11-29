import asyncio
import asyncpg
import redis.asyncio as redis
from functools import lru_cache
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Depends, HTTPException, status, Security

from . import models, auth, database

app = FastAPI(title="Securify AI - Ingest & Core API")

Instrumentator().instrument(app).expose(app)

# Use a function for dependency injection of the pool
# This allows us to easily get the pool in our endpoints
@lru_cache()
def get_app_state():
    return app.state

# Updated dependency generators
async def get_redis_dependency():
    yield get_app_state().redis

async def get_postgres_conn_dependency():
    pool = get_app_state().postgres_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool not initialized")
    async with pool.acquire() as connection:
        yield connection

@app.on_event("startup")
async def startup():
    """
    On startup, connect to databases and create pools.
    """
    app.state.redis = await database.get_redis()

    # Create connection pool instead of single connection
    for _ in range(10):
        try:
            app.state.postgres_pool = await database.create_postgres_pool()
        
            # Use the pool to get a connection and create table
            async with app.state.postgres_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS anomalies (
                        id SERIAL PRIMARY KEY,
                        source_ip VARCHAR(100),
                        score FLOAT,
                        event_type VARCHAR(100),
                        timestamp TIMESTAMPTZ,
                        details JSONB
                    );
                """)
            print("Connected to PostgreSQL and 'anomalies' table is ready.")
            break
        except Exception as e:
            print(f"Postgres not ready yet, retrying... ({e})")
            await asyncio.sleep(2)
            
@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.close()
    if hasattr(app.state, "postgres_pool"):
        await app.state.postgres_pool.close()
import asyncio
import asyncpg
import redis.asyncio as redis
from functools import lru_cache
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI, Depends, HTTPException, status, Security

from . import models, auth, database

app = FastAPI(title="Securify AI - Ingest & Core API")

Instrumentator().instrument(app).expose(app)

# Use a function for dependency injection of the pool
# This allows us to easily get the pool in our endpoints
@lru_cache()
def get_app_state():
    return app.state

# Updated dependency generators
async def get_redis_dependency():
    yield get_app_state().redis

async def get_postgres_conn_dependency():
    pool = get_app_state().postgres_pool
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool not initialized")
    async with pool.acquire() as connection:
        yield connection

@app.on_event("startup")
async def startup():
    """
    On startup, connect to databases and create pools.
    """
    app.state.redis = await database.get_redis()

    # Create connection pool instead of single connection
    for _ in range(10):
        try:
            app.state.postgres_pool = await database.create_postgres_pool()
        
            # Use the pool to get a connection and create table
            async with app.state.postgres_pool.acquire() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS anomalies (
                        id SERIAL PRIMARY KEY,
                        source_ip VARCHAR(100),
                        score FLOAT,
                        event_type VARCHAR(100),
                        timestamp TIMESTAMPTZ,
                        details JSONB
                    );
                """)
            print("Connected to PostgreSQL and 'anomalies' table is ready.")
            break
        except Exception as e:
            print(f"Postgres not ready yet, retrying... ({e})")
            await asyncio.sleep(2)
            
@app.on_event("shutdown")
async def shutdown():
    await app.state.redis.close()
    if hasattr(app.state, "postgres_pool"):
        await app.state.postgres_pool.close()

# Health Probes for Kubernetes
@app.get("/healthz", status_code=status.HTTP_200_OK, tags=["SRE"])
async def health_check():
    return {"status": "ok"}

@app.get("/readyz", status_code=status.HTTP_200_OK, tags=["SRE"])
async def readiness_check():
    try:
        await app.state.redis.ping()
        if not hasattr(app.state, "postgres_pool") or app.state.postgres_pool is None:
             raise Exception("Postgres pool not initialized")
        
        async with app.state.postgres_pool.acquire() as conn:
             await conn.execute("SELECT 1")
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {e}")

# Phase 1: Ingestion Endpoint
@app.post(
    "/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Ingestion"],
    # Requires a token with the "ingest" scope
    dependencies=[Security(auth.verify_jwt, scopes=["ingest"])]
)
async def ingest_event(
    event: models.IngestEvent,
    r: redis.Redis = Depends(lambda: app.state.redis)
):
    """
    Ingests a validated security event.
    Requires a valid M2M JWT with 'ingest' scope.
    """
    await database.add_event_to_stream(event, r)
    return {"status": "event accepted"}

# Phase 2: Anomaly Reporting Endpoint
@app.post(
    "/api/v1/anomaly",
    status_code=status.HTTP_201_CREATED,
    tags=["Anomaly"],
    # Requires a token with the "report_anomaly" scope
    dependencies=[Security(auth.verify_jwt, scopes=["report_anomaly"])]
)
async def report_anomaly(
    anomaly: models.AnomalyReport,
    conn: asyncpg.Connection = Depends(get_postgres_conn_dependency)
):
    """
    Endpoint for the ML service to report detected anomalies.
    Requires a valid JWT with 'report_anomaly' scope.
    """
    await database.log_anomaly_to_db(anomaly, conn)
    return {"status": "anomaly logged"}

# Phase 3: Dashboard Data Endpoint
@app.get(
    "/api/v1/anomalies",
    tags=["Dashboard"],
    # Requires a token with the "dashboard:read" scope
    dependencies=[Security(auth.verify_jwt, scopes=["dashboard:read"])]
)
async def get_anomalies(
    conn: asyncpg.Connection = Depends(get_postgres_conn_dependency)
):
    """
    Secure endpoint for the Streamlit dashboard to fetch anomalies.
    Requires a valid user JWT with 'dashboard:read' scope.
    """
    anomalies = await database.fetch_anomalies_from_db(conn)
    return anomalies