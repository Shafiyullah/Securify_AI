FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the model file
# (This file must be generated locally first by running train_model.py)
COPY model/model.joblib /app/model/model.joblib

# Copy the worker application
COPY ./worker /app/worker

# Run the worker script
CMD ["python", "-m", "worker.run_worker"]