# Securify AI: Usage & Production Guide

This guide explains how to use **Securify AI** in real-world environments and how to prepare it for production.

---

## 1. Real-World Use Cases

Securify AI is designed to be the "central brain" of your security infrastructure.

### A. Corporate & Internal Security
**Goal:** Detect compromised employee accounts.
-   **Integration:** Connect your VPN or Active Directory logs.
-   **What it catches:** An employee logging in from an unusual country or at 3 AM.

### B. Cloud Infrastructure
**Goal:** Protect servers from brute-force attacks.
-   **Integration:** Forward `/var/log/auth.log` (SSH logs) from your Linux servers.
-   **What it catches:** Repeated failed root login attempts.

### C. Banking & Fintech
**Goal:** Account Takeover Prevention.
-   **Integration:** Call the Ingest API directly from your Login backend.
-   **What it catches:** "Low-and-slow" attacks where a botnet tries entering stolen passwords across thousands of accounts.

---

## 2. Integration Guide

### Step 0: Generate an API Key
Before you can send data, you need an API Token (like a password for robots).
1.  Open your terminal in the project folder.
2.  Run the key generator:
    ```bash
    python scripts/generate_token.py
    ```
3.  Copy the output (starts with `ey...`). This is your `YOUR_TOKEN`.

### Option A: The "One-Liner" (For Sysadmins)

Use the included **Log Shipper** to watch a log file and forward events automatically.

```bash
# Run this on your server
python integrations/log-shipper/log_shipper.py --file /var/log/auth.log --token YOUR_TOKEN
```

### Option B: The Python SDK (For Developers)
Use the `SecurifyClient` library to report events from your code.

```python
from integrations.python_client.securify_client import SecurifyClient

client = SecurifyClient(api_url="http://securify-api:8000", api_token="YOUR_TOKEN")

# When a user logs in:
client.log_login(username="alice", success=True, ip_address="1.2.3.4")
```

### Option C: Direct API (For Any Language)
Send a JSON `POST` request to `/ingest`.

**Endpoint:** `POST /ingest`
```json
{
  "event_id": "uuid-1234",
  "timestamp": "2023-10-27T10:00:00Z",
  "source_ip": "10.0.0.1",
  "event_type": "LOGIN_ATTEMPT",
  "username": "admin",
  "success": false
}
```

---

## 3. Production Readiness Checklist

To take this from a prototype to a production system, you must address the following:

### [Critical] Data Persistence
By default, Docker Compose stores data in containers. If they restart, data is lost.
**Fix:** Add volumes to `docker-compose.yml`:
```yaml
postgres:
  volumes:
    - ./data/postgres:/var/lib/postgresql/data
```

### [High] HTTPS / SSL
Do not expose the API (`http://localhost:8000`) directly to the internet.
**Fix:** Put Nginx or Traefik in front with a simple SSL certificate (Let's Encrypt).

### [High] Secrets Management
Do not keep `JWT_SECRET_KEY` in `.env` files committed to Git.
**Fix:** Use Docker Secrets or Kubernetes Secrets.

---

## 4. Managing Access (Revoking Keys)

Since these tokens are "stateless" (like a printed ticket), you cannot delete just one specific token.

**To revoke access for everyone (e.g., if a key is stolen):**
1.  Open your `.env` file.
2.  Change the `JWT_SECRET_KEY` to something new.
3.  Restart your services (`docker-compose restart`).
    *   *Result:* All old tokens immediately stop working.
    *   *Action:* You must generate new tokens for your trusted systems.

