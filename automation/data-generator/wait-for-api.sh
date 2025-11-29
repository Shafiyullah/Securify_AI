#!/bin/sh
# wait-for-api.sh

# These are the service names from your docker-compose.yml
HOST="event-ingest-stream"
PORT="8000"
TIMEOUT=30

echo "Waiting for API service at $HOST:$PORT to be ready..."

# Loop for a set number of seconds
for i in $(seq 1 $TIMEOUT); do
  # Check if the port is open using netcat (nc)
  if nc -z -w 1 $HOST $PORT; then
    echo "API is up! Starting data generation..."
    # Success! Run the command that was passed as an argument.
    exec "$@"
  fi
  
  echo "Still waiting... ($i/$TIMEOUT)"
  sleep 1
done

# If the loop finishes, the API never came up.
echo "Error: API not ready within $TIMEOUT seconds. Exiting."
exit 1