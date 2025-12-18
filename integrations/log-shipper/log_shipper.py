import time
import os
import argparse
import logging
import re
import requests
import uuid
import datetime
import socket

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class LogShipper:
    def __init__(self, log_file, api_url, api_token):
        self.log_file = log_file
        self.api_url = api_url.rstrip("/") + "/ingest"
        self.api_token = api_token
        self.hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)

    def follow(self):
        """Generator that yields new lines in a file (like tail -f)."""
        self.file.seek(0, 2)  # Go to the end of the file
        while True:
            line = self.file.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line

    def parse_line(self, line):
        """
        Naive parser for demonstration.
        Real-world usage would use Regex for Auth.log or Nginx logs.
        """
        line = line.strip()
        if not line:
            return None

        # SSH Login
        if "Failed password" in line or "Accepted password" in line:
            success = "Accepted" in line
            user_match = re.search(r"for (\w+)", line)
            ip_match = re.search(r"from ([\d\.]+)", line)
            
            username = user_match.group(1) if user_match else "unknown"
            source_ip = ip_match.group(1) if ip_match else "0.0.0.0"

            return {
                "event_id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                "source_ip": source_ip,
                "event_type": "LOGIN_ATTEMPT",
                "username": username,
                "success": success
            }
        
        return None

    def send_event(self, event):
        try:
            headers = {"Authorization": f"Bearer {self.api_token}"}
            resp = requests.post(self.api_url, json=event, headers=headers, timeout=2)
            if resp.status_code == 202:
                logging.info(f"Sent event: {event['username']} (Success: {event['success']})")
            else:
                logging.warning(f"Failed to send: {resp.status_code} - {resp.text}")
        except Exception as e:
            logging.error(f"Error sending event: {e}")

    def run(self):
        logging.info(f"Starting Log Shipper on {self.log_file} -> {self.api_url}")
        
        if not os.path.exists(self.log_file):
            # Create dummy file if not exists for testing
            with open(self.log_file, 'w') as f:
                f.write("Log file created by Securify Shipper.\n")

        with open(self.log_file, 'r') as f:
            self.file = f
            for line in self.follow():
                event = self.parse_line(line)
                if event:
                    self.send_event(event)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Securify AI Log Shipper")
    parser.add_argument("--file", required=True, help="Path to log file to watch")
    parser.add_argument("--url", default="http://localhost:8000", help="Securify API URL")
    parser.add_argument("--token", required=True, help="JWT Ingest Token")
    
    args = parser.parse_args()
    
    shipper = LogShipper(args.file, args.url, args.token)
    shipper.run()
