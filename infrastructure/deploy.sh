#!/bin/bash
set -eo pipefail

NAMESPACE="securify-ai"

echo "--- DEPLOYING Securify AI to namespace: ${NAMESPACE} ---"

# 1. Apply Namespace
echo "Ensuring namespace '${NAMESPACE}' exists..."
kubectl create namespace ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 2. Create Secrets (do this first!)
# These should be created from env vars or a vault, not hardcoded
kubectl create secret generic postgres-secret \
    --from-literal=POSTGRES_PASSWORD='YOUR PASSWORDHERE' \
    -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

kubectl create secret generic securify-jwt-secret \
    --from-literal=JWT_SECRET_KEY='SECRET KEY HERE' \
    -n ${NAMESPACE} --dry-run=client -o yaml | kubectl apply -f -

# 3. Apply all other resources
echo "Applying dependencies (Redis, Postgres)..."
kubectl apply -f k8s/01-redis.yaml -n ${NAMESPACE}
kubectl apply -f k8s/02-postgres.yaml -n ${NAMESPACE}

echo "Applying core application services..."
kubectl apply -f k8s/03-ingest-api.yaml -n ${NAMESPACE}
kubectl apply -f k8s/04-ml-service.yaml -n ${NAMESPACE}
kubectl apply -f k8s/05-dashboard.yaml -n ${NAMESPACE}

echo "Applying Zero Trust Network Policies..."
kubectl apply -f k8s/06-network-policies.yaml -n ${NAMESPACE}

echo "--- DEPLOYMENT APPLIED ---"
echo "Waiting for all deployments to be ready..."

# Wait for all deployments in the namespace to be ready
kubectl rollout status deployment -n ${NAMESPACE} --timeout=300s

echo "--- ✅ Securify AI is LIVE ---"