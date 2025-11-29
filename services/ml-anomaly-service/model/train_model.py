import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
import os

print("Training a dummy Isolation Forest model...")

# Create some dummy "normal" data (e.g., login counts per IP)
# 1000 samples, 2 features (e.g., login_fails, file_changes)
X_train = np.random.rand(1000, 2)
X_train[:, 0] = X_train[:, 0] * 5  # Feature 1 (0-5)
X_train[:, 1] = X_train[:, 1] * 10 # Feature 2 (0-10)

# Train the model
model = IsolationForest(contamination=0.05, random_state=42)
model.fit(X_train)

# Save the model
model_path = os.path.join(os.path.dirname(__file__), "model.joblib")
joblib.dump(model, model_path)

print(f"Model saved to {model_path}")

# Test with a clear anomaly
anomaly = np.array([[50, 100]]) # 50 failed logins, 100 file changes
score = model.decision_function(anomaly)
pred = model.predict(anomaly)
print(f"Test anomaly [50, 100] score: {score[0]} (Prediction: {pred[0]})")