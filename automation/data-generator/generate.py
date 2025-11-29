import httpx
import asyncio
import random
import datetime
import time
import os
from jose import jwt

API_URL = os.environ.get("INGEST_API_URL", "http://event-ingest-stream:8000/ingest")
SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("No JWT_SECRET_KEY set for application. Please set the environment variable.")
ALGORITHM = "HS256"

def create_token():
    payload = {
        "sub": "data-generator",
        "scope": "ingest"
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

HEADERS = {
    "Authorization": f"Bearer {create_token()}",
    "Content-Type": "application/json"
}

async def send_event(client: httpx.AsyncClient, event_id: int, semaphore: asyncio.Semaphore):
    """Sends a single, randomly generated security event."""
    ip = f"192.168.{random.randint(1, 254)}.{random.randint(1, 254)}"
    event = {
        "event_id": f"evt_{event_id}_{int(time.time())}",
        "timestamp": datetime.datetime.now().isoformat(),
        "source_ip": ip,
        "event_type": "LOGIN_ATTEMPT",
        "username": f"user_{random.randint(1, 100)}",
        "success": random.choice([True, True, True, False]) # 25% fail rate
    }
    
    # Wait to acquire the semaphore before running
    # This ensures only 100 requests can be active at a time
    async with semaphore:
        try:
            response = await client.post(API_URL, json=event, headers=HEADERS)
            if response.status_code != 202:
                # This is a cleaner error message
                print(f"Failed to send event {event_id}: HTTP {response.status_code}")
        except httpx.RequestError as e:
            # We'll keep this just in case
            print(f"Request error for event {event_id}: TYPE={type(e)}, REPR={repr(e)}")

async def main():
    """Generates a high-volume burst of concurrent events."""
    event_count = 1000
    
    # Create a semaphore to limit concurrency
    concurrency_limit = 100
    semaphore = asyncio.Semaphore(concurrency_limit)
    
    print(f"Sending {event_count} events to {API_URL} (concurrency limit: {concurrency_limit})...")
    
    # Set a more generous timeout
    timeout_config = httpx.Timeout(30.0, connect=10.0)
    
    async with httpx.AsyncClient(timeout=timeout_config) as client:
        # Pass the semaphore to each task
        tasks = [send_event(client, i, semaphore) for i in range(event_count)]
        await asyncio.gather(*tasks)
        
    print(f"Sent {event_count} events.")

if __name__ == "__main__":
    asyncio.run(main())