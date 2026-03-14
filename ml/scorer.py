import os
import joblib
import numpy as np

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")

_artifact = None


def _load() -> dict:
    global _artifact
    if _artifact is None:
        if not os.path.exists(MODEL_PATH):
            from ml.train import build_model
            build_model()
        _artifact = joblib.load(MODEL_PATH)
    return _artifact


def anomaly_score(amount: float, hour: int, freq: int) -> float:
    """
    Returns a raw anomaly score from Isolation Forest.
    More negative  →  more anomalous.
    Typical range: [-0.6, 0.1].  Scores below -0.1 are suspicious.
    """
    artifact = _load()
    X = np.array([[amount, hour, freq]], dtype=float)
    X_scaled = artifact["scaler"].transform(X)
    return float(artifact["model"].score_samples(X_scaled)[0])


def is_anomalous(amount: float, hour: int, freq: int, threshold: float = -0.1) -> bool:
    return anomaly_score(amount, hour, freq) < threshold
