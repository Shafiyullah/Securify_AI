import os
from dotenv import load_dotenv
from jose import jwt, JWTError

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"

DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN")
GENERATOR_TOKEN = os.getenv("GENERATOR_TOKEN")
ML_TOKEN = os.getenv("ML_TOKEN")

def verify(token, name):
    if not token:
        print(f"⚠️ {name} token not found in environment variables.")
        return
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        print(f"✅ {name} token is VALID.")
    except JWTError as e:
        print(f"❌ {name} token is INVALID: {e}")

if __name__ == "__main__":
    if not SECRET_KEY:
        print("❌ JWT_SECRET_KEY not found in environment variables.")
    else:
        print(f"Testing with SECRET_KEY='{SECRET_KEY[:4]}***'")
        verify(DASHBOARD_TOKEN, "Dashboard")
        verify(GENERATOR_TOKEN, "Generator")
        verify(ML_TOKEN, "ML Worker")
