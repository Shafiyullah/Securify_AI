import pytest
import httpx
import os

# This would run against a live test environment
API_URL = os.environ.get("TEST_API_URL", "http://localhost:8000")

# Valid Token (sub: "test-user")
VALID_JWT = os.environ.get("TEST_VALID_JWT")
# Invalid signature
INVALID_JWT = os.environ.get("TEST_INVALID_JWT")
INVALID_SCOPE_JWT = os.environ.get("TEST_INVALID_SCOPE_JWT")

if not VALID_JWT:
    print("WARNING: TEST_VALID_JWT not set. Tests requiring auth will fail.")

VALID_EVENT = {
    "event_id": "test_evt_1",
    "timestamp": "2025-10-21T10:00:00Z",
    "source_ip": "1.2.3.4",
    "event_type": "LOGIN_ATTEMPT",
    "username": "test",
    "success": False
}

def test_ingest_endpoint_success():
    """Tests successful ingestion with a valid token."""
    if not VALID_JWT:
        pytest.skip("TEST_VALID_JWT not set")
    headers = {"Authorization": f"Bearer {VALID_JWT}"}
    with httpx.Client() as client:
        response = client.post(f"{API_URL}/ingest", json=VALID_EVENT, headers=headers)
    assert response.status_code == 202
    assert response.json() == {"status": "event accepted"}

def test_ingest_endpoint_no_auth():
    """Tests that the endpoint rejects requests with no token."""
    with httpx.Client() as client:
        response = client.post(f"{API_URL}/ingest", json=VALID_EVENT)
    assert response.status_code == 401 # or 403 depending on scheme

def test_ingest_endpoint_invalid_auth():
    """Tests that the endpoint rejects requests with a bad token."""
    if not INVALID_JWT:
        pytest.skip("TEST_INVALID_JWT not set")
    headers = {"Authorization": f"Bearer {INVALID_JWT}"}
    with httpx.Client() as client:
        response = client.post(f"{API_URL}/ingest", json=VALID_EVENT, headers=headers)
    assert response.status_code == 401

def test_ingest_endpoint_invalid_scope():
    """Tests that the endpoint rejects requests with a valid token but wrong scope."""
    if not INVALID_SCOPE_JWT:
        pytest.skip("TEST_INVALID_SCOPE_JWT not set")
    headers = {"Authorization": f"Bearer {INVALID_SCOPE_JWT}"}
    with httpx.Client() as client:
        response = client.post(f"{API_URL}/ingest", json=VALID_EVENT, headers=headers)
    # The API should return 403 Forbidden, not 401 Unauthorized
    assert response.status_code == 403

def test_ingest_endpoint_bad_validation():
    """Tests input validation (Tweak 1)."""
    if not VALID_JWT:
        pytest.skip("TEST_VALID_JWT not set")
    headers = {"Authorization": f"Bearer {VALID_JWT}"}
    # Missing 'username' and 'success' fields
    invalid_event = {
        "event_id": "test_evt_2",
        "timestamp": "2025-10-21T10:00:00Z",
        "source_ip": "1.2.3.4",
        "event_type": "LOGIN_ATTEMPT",
    }
    with httpx.Client() as client:
        response = client.post(f"{API_URL}/ingest", json=invalid_event, headers=headers)
    # FastAPI/Pydantic returns 422 Unprocessable Entity
    assert response.status_code == 422