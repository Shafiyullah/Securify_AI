import jwt
import datetime
import argparse
import sys

import os

# Try to load from environment, otherwise None
DEFAULT_SECRET = os.getenv("JWT_SECRET_KEY")

def generate_token(secret_key: str, scope: str, user: str, expires_minutes: int = 1440):
    if not secret_key:
        print("Error: No SECRET_KEY provided. Set JWT_SECRET_KEY env var or use --secret argument.")
        return None

    payload = {
        "sub": user,
        "scope": scope,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expires_minutes),
        "iat": datetime.datetime.utcnow()
    }
    
    try:
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        return token
    except Exception as e:
        print(f"Error generating token: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate JWT Token for Securify AI")
    parser.add_argument("--secret", default=DEFAULT_SECRET, help="Your JWT_SECRET_KEY (must match .env)")
    parser.add_argument("--user", default="admin-cli", help="Username for the token")
    parser.add_argument("--scope", default="ingest", help="Scope (ingest, report_anomaly, dashboard:read)")
    
    args = parser.parse_args()
    
    print(f"Generating token for user '{args.user}' with scope '{args.scope}'...")
    token = generate_token(args.secret, args.scope, args.user)
    
    if token:
        print("\n--- YOUR API TOKEN ---")
        print(token)
        print("----------------------\n")
        print("Usage:")
        print(f"Authorization: Bearer {token}")
