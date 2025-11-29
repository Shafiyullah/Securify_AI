import redis
import os
import time
import requests
import json
import pandas as pd
import traceback
from . import health_server, model_loader
from jose import jwt

# Config
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
API_HOST = os.environ.get("API_HOST", "http://event-ingest-stream-svc:8000")
API_URL = f"{API_HOST}/api/v1/anomaly"
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No JWT_SECRET_KEY set for application. Please set the environment variable.")
ALGORITHM = "HS256"

def create_token():
    payload = {
        "sub": "ml-worker",
        "scope": "report_anomaly"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

HEADERS = {"Authorization": f"Bearer {create_token()}", "Content-Type": "application/json"}

STREAM_NAME = "events:raw"
CONSUMER_GROUP = "ml-workers"
CONSUMER_NAME = os.environ.get("HOSTNAME", "local-worker-1")

def create_consumer_group(r: redis.Redis):
    try:
        r.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        print(f"Created consumer group '{CONSUMER_GROUP}' on stream '{STREAM_NAME}'.")
    except redis.exceptions.ResponseError as e:
        if "name already exists" in str(e):
            print(f"Consumer group '{CONSUMER_GROUP}' already exists.")
        else:
            raise

def process_batch(events: list, model):
    parsed_data = []
    
    # 1. Parse JSON data safely
    for _id, data in events:
        try:
            event_json = json.loads(data[b'data'])
            parsed_data.append(event_json)
        except Exception as e:
            print(f"Skipping malformed event {_id}: {e}")
            continue

    if not parsed_data:
        return

    # 2. Create DataFrame
    df = pd.DataFrame(parsed_data)

    # 3. Process LOGIN_ATTEMPT events
    if 'event_type' in df.columns:
        login_df = df[df['event_type'] == 'LOGIN_ATTEMPT'].copy()
        
        if not login_df.empty:
            print(f"Processing {len(login_df)} login events...")
            login_df['success'] = login_df['success'].astype(bool)
            features_df = login_df.groupby('source_ip').agg(
                total_logins=('event_id', 'count'),
                failed_logins=('success', lambda x: (x == False).sum())
            )
            # Feature Engineering
            features_df['dummy_file_changes'] = features_df['failed_logins'] / 2.0 
            X_predict = features_df[['failed_logins', 'dummy_file_changes']].to_numpy()
            
            if X_predict.shape[0] > 0:
                scores = model.decision_function(X_predict)
                
                for (ip, row), score in zip(features_df.iterrows(), scores):
                    # Anomaly threshold
                    if score < 0.1:
                        print(f"ANOMALY DETECTED! IP: {ip}, Score: {score}")
                        report = {
                            "source_ip": ip,
                            "score": 1 - (score + 1) / 2, # Normalize score
                            "event_type": "AGG_LOGIN_FAIL",
                            "timestamp": pd.Timestamp.now().isoformat(),
                            "details": row.to_dict()
                        }
                        try:
                            requests.post(API_URL, json=report, headers=HEADERS, timeout=2)
                        except requests.RequestError as e:
                            print(f"Failed to report anomaly: {e}")

    # 4. Process FILE_CHANGE events
        file_df = df[df['event_type'] == 'FILE_CHANGE'].copy()
        if not file_df.empty:
            # This is where logic for file changes would go.
            # For now, we just log them to prevent silent data loss.
            print(f"INFO: Received and acknowledged {len(file_df)} FILE_CHANGE events. (No model logic implemented.)")

def main():
    print("Starting ML Anomaly Worker...")
    health_server.start_server()

    model = model_loader.load_model()
    if model is None:
        print("Fatal: Could not load model. Exiting.")
        return
    health_server.MODEL_IS_READY = True

    r = redis.Redis(host=REDIS_HOST, port=6379, decode_responses=False) # Use False for raw stream reading
    r.ping()
    create_consumer_group(r)
    print("Connected to Redis.")

    while True:
        try:
            # Block for 2 seconds, fetch up to 100 items
            response = r.xreadgroup(
                CONSUMER_GROUP,
                CONSUMER_NAME,
                {STREAM_NAME: ">"},
                count=100,
                block=2000
            )
            
            if not response:
                continue

            events = response[0][1]
            
            # Ensure we process AND acknowledge
            if events:
                process_batch(events, model)
                
                # Acknowledge all event IDs in this batch
                event_ids = [e[0] for e in events]
                r.xack(STREAM_NAME, CONSUMER_GROUP, *event_ids)
                print(f"Processed and acked {len(event_ids)} events.")

        except redis.exceptions.RedisError as e:
            print(f"Redis error: {e}. Reconnecting in 5s...")
            time.sleep(5)
        except Exception as e:
            print(f"Unexpected error in main loop: {e}")
            traceback.print_exc()
            time.sleep(1)

if __name__ == "__main__":
    main()