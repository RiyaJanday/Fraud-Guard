"""
Loads trained model artifacts once and serves predictions. Per project
requirements: NEVER retrains during inference — if no trained model exists
yet, this raises ModelNotLoadedException rather than silently training one
or falling back to a stub.
"""

import json
import time
from typing import Optional

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.exceptions import ModelNotLoadedException
from app.core.logging import logger
from app.ml_engine.shap_service import explain_instance, generate_explanation
from app.models.fraud_prediction import Decision

settings = get_settings()


class FraudPredictor:
    """
    Holds the loaded model/scaler/explainer in memory. Constructed once (see
    get_predictor() below) and reused across requests — loading joblib
    artifacts from disk on every prediction would add unnecessary latency.
    """

    def __init__(self) -> None:
        self.model = None
        self.scaler = None
        self.explainer = None
        self.feature_columns: Optional[list[str]] = None
        self.model_version: Optional[str] = None
        self._loaded = False

    def load(self) -> None:
        import joblib

        model_path = settings.MODEL_DIR / settings.MODEL_FILE
        scaler_path = settings.MODEL_DIR / settings.SCALER_FILE
        explainer_path = settings.MODEL_DIR / settings.SHAP_EXPLAINER_FILE
        metrics_path = settings.MODEL_DIR / settings.METRICS_FILE

        if not model_path.exists() or not scaler_path.exists():
            raise ModelNotLoadedException(
                f"No trained model found in {settings.MODEL_DIR}. Run `python train_model.py` "
                "from the fraudguard-backend/ directory first."
            )

        self.model = joblib.load(model_path)
        self.scaler = joblib.load(scaler_path)
        self.explainer = joblib.load(explainer_path) if explainer_path.exists() else None

        if metrics_path.exists():
            with open(metrics_path) as f:
                metadata = json.load(f)
            self.model_version = metadata.get("model_version", settings.MODEL_VERSION)
            self.feature_columns = metadata.get("feature_columns")
        else:
            self.model_version = settings.MODEL_VERSION

        if not self.feature_columns:
            # Fallback matching preprocessing.FEATURE_COLUMNS, in case metrics.json
            # is missing/older than expected.
            self.feature_columns = [f"V{i}" for i in range(1, 29)] + ["Amount", "Amount_log", "Hour"]

        self._loaded = True
        logger.info("Fraud model loaded | version={} explainer_available={}", self.model_version, self.explainer is not None)

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def predict(self, time_feature: float, amount: float, v_features: dict) -> dict:
        """
        time_feature: seconds elapsed (same semantics as the dataset's Time column)
        amount: transaction amount
        v_features: dict like {"V1": -1.359, ..., "V28": -0.021}

        Returns a dict matching exactly what the /predict API and FraudPrediction
        model need: is_fraud, fraud_probability, risk_score, confidence, decision,
        latency_ms, top_shap_features, explanation, model_version.
        """
        self.ensure_loaded()
        start = time.perf_counter()

        row = {f"V{i}": float(v_features.get(f"V{i}", 0.0)) for i in range(1, 29)}
        row["Amount"] = float(amount)
        row["Amount_log"] = float(np.log1p(amount))
        row["Hour"] = float((time_feature // 3600) % 24)

        X = pd.DataFrame([row], columns=self.feature_columns)
        X_scaled = pd.DataFrame(self.scaler.transform(X), columns=X.columns)

        proba = float(self.model.predict_proba(X_scaled)[0, 1])
        is_fraud = proba >= 0.5
        risk_score = round(proba * 100, 2)
        # Confidence: 0 at the decision boundary (proba=0.5, maximally
        # uncertain), 1 when the model is maximally sure either way.
        confidence = round(2 * abs(proba - 0.5), 4)

        if proba < settings.RISK_THRESHOLD_APPROVE:
            decision = Decision.APPROVE
        elif proba < settings.RISK_THRESHOLD_BLOCK:
            decision = Decision.MFA_REQUIRED
        else:
            decision = Decision.BLOCKED

        top_features: list[dict] = []
        if self.explainer is not None:
            try:
                top_features = explain_instance(self.explainer, X_scaled)
            except Exception as exc:  # noqa: BLE001 — a SHAP failure should degrade, not crash the prediction
                logger.error("SHAP explanation failed, continuing without it: {}", exc)

        explanation = generate_explanation(top_features, is_fraud, risk_score)
        latency_ms = round((time.perf_counter() - start) * 1000, 2)

        return {
            "is_fraud": is_fraud,
            "fraud_probability": round(proba, 6),
            "risk_score": risk_score,
            "confidence": confidence,
            "decision": decision,
            "latency_ms": latency_ms,
            "top_shap_features": top_features,
            "explanation": explanation,
            "model_version": self.model_version,
        }


_predictor: Optional[FraudPredictor] = None


def get_predictor() -> FraudPredictor:
    """Module-level singleton — the same loaded model is reused across all requests."""
    global _predictor
    if _predictor is None:
        _predictor = FraudPredictor()
    return _predictor
