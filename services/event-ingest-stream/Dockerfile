FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt .

# Install curl so the healthcheck can work
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    libpq-dev \
    curl && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]