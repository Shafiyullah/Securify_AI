import requests
import uuid
import datetime
import socket
import logging
from typing import Optional

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SecurifyClient")

class SecurifyClient:
    """
    A simple client for integrating with the Securify AI Ingest API.
    """
    
    def __init__(self, api_url: str, api_token: str, timeout: int = 2):
        self.api_url = api_url.rstrip("/") + "/ingest"
        self.api_token = api_token
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        })

    def _send_event(self, event_data: dict):
        """Internal method to send the event to the API."""
        try:
            response = self.session.post(self.api_url, json=event_data, timeout=self.timeout)
            response.raise_for_status()
            logger.debug(f"Event sent successfully: {event_data['event_id']}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send event to Securify AI: {e}")
            return False

    def log_login(self, username: str, success: bool, ip_address: Optional[str] = None):
        """
        Log a user login attempt.
        """
        if not ip_address:
            # Best effort to get local IP if not provided
            try:
                ip_address = socket.gethostbyname(socket.gethostname())
            except:
                ip_address = "127.0.0.1"

        payload = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "source_ip": ip_address,
            "event_type": "LOGIN_ATTEMPT",
            "username": username,
            "success": success
        }
        return self._send_event(payload)

    def log_file_change(self, file_path: str, user_id: str, ip_address: Optional[str] = None):
        """
        Log a sensitive file access or modification.
        """
        if not ip_address:
             try:
                ip_address = socket.gethostbyname(socket.gethostname())
             except:
                ip_address = "127.0.0.1"

        payload = {
            "event_id": str(uuid.uuid4()),
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "source_ip": ip_address,
            "event_type": "FILE_CHANGE",
            "file_path": file_path,
            "user_id": user_id
        }
        return self._send_event(payload)

if __name__ == "__main__":
    # Example Usage
    print("Testing SecurifyClient...")
    client = SecurifyClient("http://localhost:8000", "test-token")
    # This will likely fail with 403/401 unless there is a real server with this token
    # But it demonstrates the call.
    client.log_login("test_user", False, "10.0.0.1")
