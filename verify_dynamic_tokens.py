import sys
from unittest.mock import MagicMock

# Mock dependencies
sys.modules["httpx"] = MagicMock()
sys.modules["redis"] = MagicMock()
sys.modules["pandas"] = MagicMock()
sys.modules["streamlit"] = MagicMock()
sys.modules["requests"] = MagicMock()
sys.modules["asyncpg"] = MagicMock()
sys.modules["prometheus_fastapi_instrumentator"] = MagicMock()
sys.modules["fastapi"] = MagicMock()
sys.modules["pydantic"] = MagicMock()

import os
from dotenv import load_dotenv
from jose import jwt

load_dotenv()

# Import modules to test
sys.path.append(os.path.join(os.getcwd(), "automation", "data-generator"))
sys.path.append(os.path.join(os.getcwd(), "services", "ml-anomaly-service", "worker"))
sys.path.append(os.path.join(os.getcwd(), "services", "security-dashboard"))

try:
    import generate
    print("✅ Loaded generate.py")
except ImportError as e:
    print(f"❌ Failed to load generate.py: {e}")

try:
    import run_worker
    print("✅ Loaded run_worker.py")
except ImportError as e:
    print(f"❌ Failed to load run_worker.py: {e}")

try:
    import app as dashboard_app
    print("✅ Loaded app.py")
except ImportError as e:
    print(f"❌ Failed to load app.py: {e}")

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

def verify(token, name):
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token.split(" ")[1]
            
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ {name} token is VALID. Scope: {payload.get('scope')}")
    except Exception as e:
        print(f"❌ {name} token is INVALID: {e}")

if __name__ == "__main__":
    if not SECRET_KEY:
        print("❌ JWT_SECRET_KEY not found in environment variables.")
        sys.exit(1)
    print(f"Testing with SECRET_KEY='{SECRET_KEY[:4]}***'")
    
    # Test Generator
    if 'generate' in sys.modules:
        try:
            token = generate.create_token()
            verify(token, "Generator")
        except AttributeError:
             print("❌ generate.create_token not found")

    # Test ML Worker
    if 'run_worker' in sys.modules:
        try:
            token = run_worker.create_token()
            verify(token, "ML Worker")
        except AttributeError:
             print("❌ run_worker.create_token not found")

    # Test Dashboard
    if 'dashboard_app' in sys.modules:
        try:
            token = dashboard_app.mock_login("admin", "admin")
            verify(token, "Dashboard")
        except AttributeError:
             print("❌ dashboard_app.mock_login not found")
