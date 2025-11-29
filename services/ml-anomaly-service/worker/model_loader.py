import joblib
import os

MODEL_PATH = os.environ.get("MODEL_PATH", "/app/model/model.joblib")
model = None

def load_model():
    """Loads the ML model from disk into memory."""
    global model
    try:
        model = joblib.load(MODEL_PATH)
        print(f"Successfully loaded model from {MODEL_PATH}")
        return model
    except FileNotFoundError:
        print(f"Error: Model file not found at {MODEL_PATH}")
        return None