from flask import Flask, jsonify
import threading

app = Flask(__name__)

# Global flag to be set by the main worker
MODEL_IS_READY = False

@app.route("/healthz")
def liveness_probe():
    """
    Liveness probe: Is the Flask server running?
    """
    return jsonify({"status": "alive"}), 200

@app.route("/readyz")
def readiness_probe():
    """
    Readiness probe: Is the model loaded and ready to serve?
    """
    if MODEL_IS_READY:
        return jsonify({"status": "ready"}), 200
    else:
        return jsonify({"status": "loading_model"}), 503

def start_server():
    """Starts the Flask server in a separate thread."""
    print("Starting health probe server on port 5000...")
    thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True)
    thread.start()