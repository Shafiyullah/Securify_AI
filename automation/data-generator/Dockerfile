# contents for automation/data-generator/Dockerfile

FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

COPY generate.py .

# Copy the wait script into the container's /app directory
COPY wait-for-api.sh /app/

# Make the script executable
RUN chmod +x /app/wait-for-api.sh

# We just run the script once
CMD ["python", "generate.py"]