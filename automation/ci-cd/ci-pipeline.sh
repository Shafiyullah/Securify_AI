#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -eo pipefail

# --- CONFIG ---
# These would be set by the CI/CD system (e.g., GitLab CI variables)
IMAGE_REGISTRY="my-registry.com/securify-ai"
IMAGE_TAG=${CI_COMMIT_SHA:-latest} # Use commit SHA or 'latest'

# Define service directories
INGEST_SERVICE_DIR="services/event-ingest-stream"
ML_SERVICE_DIR="services/ml-anomaly-service"
DASHBOARD_SERVICE_DIR="services/security-dashboard"

# --- STAGES ---
stage_test() {
    echo "--- 1. RUNNING TESTS (Python Pytest) ---"
    # Assuming a test environment is running, or using mocks
    python3 -m pytest automation/tests/
    echo "--- ✅ Tests Passed ---"
}

stage_security_scan() {
    echo "--- 2. RUNNING SECURITY SCANS (Python/Bash) ---"

    echo "[SAST Gate]"
    # Run Bandit and output to JSON
    bandit -r ./services -f json -o bandit-report.json
    # Run the Python parser script
    python3 automation/ci-cd/parse_bandit.py
    
    echo "[Dependency Check Gate]"
    # Check all requirements files
    pip-audit -r ${INGEST_SERVICE_DIR}/requirements.txt
    pip-audit -r ${ML_SERVICE_DIR}/requirements.txt
    pip-audit -r ${DASHBOARD_SERVICE_DIR}/requirements.txt

    echo "--- ✅ Security Scans Passed ---"
}

stage_build() {
    echo "--- 3. BUILDING DOCKER IMAGES ---"
    
    docker build -t ${IMAGE_REGISTRY}/event-ingest-stream:${IMAGE_TAG} -f ${INGEST_SERVICE_DIR}/Dockerfile .
    docker build -t ${IMAGE_REGISTRY}/ml-anomaly-service:${IMAGE_TAG} -f ${ML_SERVICE_DIR}/Dockerfile .
    docker build -t ${IMAGE_REGISTRY}/security-dashboard:${IMAGE_TAG} -f ${DASHBOARD_SERVICE_DIR}/Dockerfile .
    
    echo "--- ✅ Docker Images Built ---"
}

stage_container_scan() {
    echo "--- 4. SCANNING DOCKER IMAGES (Bash/Trivy) ---"

    # Scan each image for CRITICAL vulnerabilities
    trivy image --exit-code 1 --severity CRITICAL ${IMAGE_REGISTRY}/event-ingest-stream:${IMAGE_TAG}
    trivy image --exit-code 1 --severity CRITICAL ${IMAGE_REGISTRY}/ml-anomaly-service:${IMAGE_TAG}
    trivy image --exit-code 1 --severity CRITICAL ${IMAGE_REGISTRY}/security-dashboard:${IMAGE_TAG}

    echo "--- ✅ Container Scans Passed ---"
}

stage_push() {
    echo "--- 5. PUSHING IMAGES TO REGISTRY ---"
    # Assumes `docker login` has already happened
    docker push ${IMAGE_REGISTRY}/event-ingest-stream:${IMAGE_TAG}
    docker push ${IMAGE_REGISTRY}/ml-anomaly-service:${IMAGE_TAG}
    docker push ${IMAGE_REGISTRY}/security-dashboard:${IMAGE_TAG}
    echo "--- ✅ Images Pushed ---"
}

stage_deploy() {
    echo "--- 6. DEPLOYING TO KUBERNETES (Bash/kubectl) ---"
    # This script contains the `kubectl apply` commands
    # We must first update the image tags in the YAML files
    echo "Setting image tag in Kubernetes manifests to: ${IMAGE_TAG}"
    # This is a simple way to do it; kustomize or helm is better
    sed -i "s|image: .*|image: ${IMAGE_REGISTRY}/event-ingest-stream:${IMAGE_TAG}|g" infrastructure/k8s/03-ingest-api.yaml
    sed -i "s|image: .*|image: ${IMAGE_REGISTRY}/ml-anomaly-service:${IMAGE_TAG}|g" infrastructure/k8s/04-ml-service.yaml
    sed -i "s|image: .*|image: ${IMAGE_REGISTRY}/security-dashboard:${IMAGE_TAG}|g" infrastructure/k8s/05-dashboard.yaml

    bash infrastructure/deploy.sh
    echo "--- ✅ Deployment Complete ---"
}

# --- MAIN EXECUTION ---
# This is the orchestration of the pipeline
stage_test
stage_security_scan
stage_build
stage_container_scan
stage_push
# stage_deploy # Often a manual step or runs on a separate 'deploy' job