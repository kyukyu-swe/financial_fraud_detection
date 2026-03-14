import os
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")


def build_model() -> None:
    rng = np.random.default_rng(42)

    # 475 normal: moderate amounts, business hours (8-20), low frequency (1-3 txn/hr)
    normal = rng.normal(
        loc=[500, 14, 2],
        scale=[200, 4, 0.8],
        size=(475, 3),
    )

    # 25 fraud-like outliers: high amounts, odd hours (1-4am), high frequency (7-10 txn/hr)
    fraud = rng.normal(
        loc=[8000, 2, 8],
        scale=[2000, 1, 1.5],
        size=(25, 3),
    )

    X = np.vstack([normal, fraud])
    # Clip to realistic bounds
    X[:, 0] = np.clip(X[:, 0], 1, 50000)    # amount
    X[:, 1] = np.clip(X[:, 1], 0, 23)        # hour
    X[:, 2] = np.clip(X[:, 2], 0, 20)        # frequency

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
    model.fit(X_scaled)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "scaler": scaler}, MODEL_PATH)
    print("[ml] Isolation Forest model built and saved.")


def ensure_model() -> None:
    if not os.path.exists(MODEL_PATH):
        build_model()


if __name__ == "__main__":
    build_model()
