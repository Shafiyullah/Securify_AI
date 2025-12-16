import redis.asyncio as redis_async
import redis
import os
import asyncio
import aiohttp
import orjson
import pandas as pd
import traceback
import numpy as np
from . import health_server, model_loader
from jose import jwt

# Config
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
API_HOST = os.environ.get("API_HOST", "http://event-ingest-stream-svc:8000")
API_URL = f"{API_HOST}/api/v1/anomaly"
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

if not SECRET_KEY:
    raise ValueError("No JWT_SECRET_KEY set. Application cannot start securely.")

ALGORITHM = "HS256"

# -- Token Management --
def create_token():
    payload = {
        "sub": "ml-worker",
        "scope": "report_anomaly"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

# -- Constants --
STREAM_NAME = "events:raw"
CONSUMER_GROUP = "ml-workers"
CONSUMER_NAME = os.environ.get("HOSTNAME", "local-worker-1")
BATCH_SIZE = 500  # Increased batch size for async efficiency
BLOCK_MS = 2000

# -- Stats for Z-Score --
# Simple in-memory stats for demonstration. 
# In production, this might be stored in Redis for persistence across restarts.
IP_STATS = {} 
STATS_WINDOW = 50 # Keep last N stats per IP

async def create_consumer_group(r: redis_async.Redis):
    try:
        await r.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        print(f"Created consumer group '{CONSUMER_GROUP}' on stream '{STREAM_NAME}'.")
    except redis.exceptions.ResponseError as e:
        if "name already exists" in str(e):
            print(f"Consumer group '{CONSUMER_GROUP}' already exists.")
        else:
            raise

async def report_anomaly_async(session: aiohttp.ClientSession, report: dict):
    """Fire-and-forget anomaly report (we just log errors)."""
    headers = {"Authorization": f"Bearer {create_token()}", "Content-Type": "application/json"}
    try:
        # Use aiohttp for non-blocking HTTP request
        async with session.post(API_URL, json=report, headers=headers) as resp:
            if resp.status not in (200, 201):
                text = await resp.text()
                print(f"Failed to report anomaly: {resp.status} - {text}")
            else:
                # Optional: print specific confirmation only for debug
                pass
    except Exception as e:
        print(f"Error reporting anomaly: {e}")

async def process_batch(events: list, model, session: aiohttp.ClientSession):
    parsed_data = []
    
    # 1. Faster Parsing with orjson
    for _id, data in events:
        try:
            # redis-py returns dict for data. Key might be bytes or str depending on decode_responses.
            # We used decode_responses=False for the redis client, so keys/values are bytes.
            payload = data.get(b'data') or data.get('data')
            event_json = orjson.loads(payload)
            parsed_data.append(event_json)
        except Exception as e:
            print(f"Skipping malformed event {_id}: {e}")
            continue

    if not parsed_data:
        return

    # 2. Optimized DataFrame Creation
    df = pd.DataFrame(parsed_data)

    # 3. Process LOGIN_ATTEMPT
    if 'event_type' in df.columns:
        # Filter in pandas is fast
        login_mask = df['event_type'] == 'LOGIN_ATTEMPT'
        if login_mask.any():
            login_df = df[login_mask].copy()
            
            # Vectorized bool conversion
            login_df['success'] = login_df['success'].astype(bool)
            
            # Aggregation
            features_df = login_df.groupby('source_ip').agg(
                total_logins=('event_id', 'count'),
                failed_logins=('success', lambda x: (~x).sum())
            )

            # --- optimization: Statistical Pre-filter ---
            suspicious_candidates = features_df[features_df['failed_logins'] > 2].copy()
            
            if not suspicious_candidates.empty:
                # Feature Engineering
                suspicious_candidates['dummy_file_changes'] = suspicious_candidates['failed_logins'] / 2.0
                X_predict = suspicious_candidates[['failed_logins', 'dummy_file_changes']].to_numpy() # Use numpy array
                
                # ML Inference
                scores = model.decision_function(X_predict)
                
                tasks = []
                for (ip, row), score in zip(suspicious_candidates.iterrows(), scores):
                    # Anomaly threshold
                    if score < 0.1:
                        print(f"ANOMALY DETECTED! IP: {ip}, Score: {score}")
                        report = {
                            "source_ip": str(ip),
                            "score": float(1 - (score + 1) / 2),
                            "event_type": "AGG_LOGIN_FAIL",
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "details": row.to_dict()
                        }
                        # Add reporting task
                        tasks.append(report_anomaly_async(session, report))
                
                # Run all reports concurrently
                if tasks:
                    await asyncio.gather(*tasks)

async def main():
    print("Starting Optimized ML Anomaly Worker (Async)...")
    health_server.start_server()

    # Load model
    model = model_loader.load_model()
    if model is None:
        print("Fatal: Could not load model. Exiting.")
        return
    health_server.MODEL_IS_READY = True

    # Reuse session
    async with aiohttp.ClientSession() as session:
        # Async Redis
        r = redis_async.Redis(host=REDIS_HOST, port=6379, decode_responses=False)
        
        try:
            await r.ping()
            await create_consumer_group(r)
            print("Connected to Redis (Async).")
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return

        while True:
            try:
                # Blocking read
                events_raw = await r.xreadgroup(
                    CONSUMER_GROUP,
                    CONSUMER_NAME,
                    {STREAM_NAME: ">"},
                    count=BATCH_SIZE,
                    block=BLOCK_MS
                )

                if not events_raw:
                    continue

                events = events_raw[0][1]

                if events:
                    await process_batch(events, model, session)
                    
                    event_ids = [e[0] for e in events]
                    # Async ack
                    await r.xack(STREAM_NAME, CONSUMER_GROUP, *event_ids)
                    if len(events) > 10: # Only log big batches to reduce noise
                        print(f"Processed batch of {len(events)} events.")

            except redis.exceptions.ConnectionError:
                print("Redis connection lost. Retrying in 5s...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"Unexpected error: {e}")
                traceback.print_exc()
                await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped.")