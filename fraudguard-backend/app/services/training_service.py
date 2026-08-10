"""
The actual training pipeline logic, extracted from train_model.py so both
the CLI script and the admin-triggered POST /model/retrain endpoint share
exactly one implementation rather than maintaining two copies that could
drift apart. train_model.py is now a thin CLI wrapper around run_training().

Also owns a small in-memory "is training currently running" tracker.
Deliberately in-process/in-memory, not a database row or Redis key — this
mirrors the same reasoning as core/rate_limit.py: the Dockerfile runs a
single Uvicorn worker, so there's exactly one process that could ever be
training at a time, and a simple threading.Lock is sufficient and doesn't
add a dependency on Redis being reachable just to check training status.
The tradeoff, stated plainly: this status resets to "not training" on every
process restart/redeploy, even if a training run happened to be interrupted
mid-flight. Acceptable here — training is only ever triggered manually by an
admin, who would notice and just retrigger it.
"""

import json
import threading
import time
from datetime import datetime, timezone
from typing import Optional

import joblib

from app.core.config import get_settings
from app.core.logging import logger
from app.database.session import SessionLocal
from app.ml_engine import evaluation, preprocessing, shap_service, training
from app.models.model_registry import ModelRegistry, ModelStatus

_lock = threading.Lock()
_state: dict = {
    "in_progress": False,
    "started_at": None,
    "finished_at": None,
    "last_result": None,  # {"version": ..., "algorithm": ..., "metrics": {...}} on success
    "last_error": None,
}


def get_status() -> dict:
    with _lock:
        return dict(_state)


def try_start() -> bool:
    """Returns False (and starts nothing) if a training run is already in progress."""
    with _lock:
        if _state["in_progress"]:
            return False
        _state["in_progress"] = True
        _state["started_at"] = datetime.now(timezone.utc).isoformat()
        _state["finished_at"] = None
        _state["last_error"] = None
        return True


def _finish(result: Optional[dict], error: Optional[str]) -> None:
    with _lock:
        _state["in_progress"] = False
        _state["finished_at"] = datetime.now(timezone.utc).isoformat()
        if result is not None:
            _state["last_result"] = result
        if error is not None:
            _state["last_error"] = error


def run_training_background(quick: bool = True) -> None:
    """
    Entry point for FastAPI's BackgroundTasks (see api/v1/model.py). Sync
    function — FastAPI runs sync background tasks in a threadpool, so this
    does NOT block the event loop / other requests while training runs, even
    though scikit-learn/XGBoost training itself is CPU-bound synchronous code.
    Swallows and records exceptions instead of raising, since there is no
    HTTP request left to return an error to by the time this runs.
    """
    try:
        metadata = run_training(quick=quick)
        _finish(
            result={
                "version": metadata["model_version"],
                "algorithm": metadata["selected_model"],
                "metrics": metadata["all_model_results"][metadata["selected_model"]],
            },
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — this IS the top-level handler, nothing above it
        logger.exception("Background retraining failed")
        _finish(result=None, error=str(exc))


def run_training(quick: bool = True) -> dict:
    """
    The full pipeline: load -> validate -> analyze -> preprocess -> engineer
    features -> split -> scale -> SMOTE -> train 3 candidates -> evaluate on
    held-out test set -> select best (Recall > F1 > Precision > ROC-AUC >
    Accuracy) -> build SHAP explainer -> save artifacts -> register in
    Postgres as ACTIVE (deactivating whatever was previously active).

    Returns the same metadata dict written to metrics.json. Raises on any
    failure — callers (train_model.py's CLI, or run_training_background
    above) decide how to surface that.
    """
    settings = get_settings()
    pipeline_start = time.perf_counter()

    # 1. Load + validate + analyze
    df = preprocessing.load_dataset()
    preprocessing.validate_dataset(df)
    analysis = preprocessing.analyze_dataset(df)
    logger.info("Dataset analysis:\n{}", json.dumps(analysis, indent=2))

    # 2. Preprocess + engineer features
    df = preprocessing.handle_missing_values(df)
    df = preprocessing.engineer_features(df)
    X, y = preprocessing.split_features_target(df)

    X_train, X_val, X_test, y_train, y_val, y_test = preprocessing.train_val_test_split(X, y)
    logger.info(
        "Split sizes | train={} ({} fraud) val={} ({} fraud) test={} ({} fraud)",
        len(X_train), int(y_train.sum()), len(X_val), int(y_val.sum()), len(X_test), int(y_test.sum()),
    )

    scaler, X_train_scaled, X_val_scaled, X_test_scaled = preprocessing.scale_features(X_train, X_val, X_test)
    X_train_res, y_train_res = preprocessing.apply_smote(X_train_scaled, y_train)

    # 3. Train all 3 candidates
    models = {}
    t0 = time.perf_counter()
    logger.info("Training Logistic Regression...")
    models["logistic_regression"] = training.train_logistic_regression(X_train_res, y_train_res, quick=quick)
    logger.info("  done in {:.1f}s", time.perf_counter() - t0)

    t0 = time.perf_counter()
    logger.info("Training Random Forest...")
    models["random_forest"] = training.train_random_forest(X_train_res, y_train_res, quick=quick)
    logger.info("  done in {:.1f}s", time.perf_counter() - t0)

    t0 = time.perf_counter()
    logger.info("Training XGBoost...")
    models["xgboost"] = training.train_xgboost(X_train_res, y_train_res, quick=quick)
    logger.info("  done in {:.1f}s", time.perf_counter() - t0)

    # 4. Evaluate all 3 on the held-out TEST set (never touched until now)
    results = {name: evaluation.evaluate_model(model, X_test_scaled, y_test) for name, model in models.items()}
    logger.info("=" * 70)
    logger.info("Model comparison (test set):")
    for name, metrics in results.items():
        logger.info(
            "  {:20s} | acc={:.4f} prec={:.4f} recall={:.4f} f1={:.4f} roc_auc={:.4f} pr_auc={:.4f}",
            name, metrics["accuracy"], metrics["precision"], metrics["recall"],
            metrics["f1_score"], metrics["roc_auc"], metrics["pr_auc"],
        )
    logger.info("=" * 70)

    val_results = {name: evaluation.evaluate_model(model, X_val_scaled, y_val) for name, model in models.items()}
    logger.info("(Validation-set metrics, for reference only — selection uses test set)")
    for name, metrics in val_results.items():
        logger.info(
            "  {:20s} | acc={:.4f} prec={:.4f} recall={:.4f} f1={:.4f}",
            name, metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1_score"],
        )

    # 5. Select best model
    best_name = evaluation.select_best_model(results)
    best_model = models[best_name]
    best_metrics = results[best_name]

    # 6. Build SHAP explainer
    background = X_train_res.sample(n=min(200, len(X_train_res)), random_state=42)
    explainer = shap_service.build_explainer(best_model, background)

    # 7. Save artifacts
    settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, settings.MODEL_DIR / settings.MODEL_FILE)
    joblib.dump(scaler, settings.MODEL_DIR / settings.SCALER_FILE)
    joblib.dump(explainer, settings.MODEL_DIR / settings.SHAP_EXPLAINER_FILE)

    version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    metadata = {
        "model_version": version,
        "algorithm": best_name,
        "feature_columns": list(X_train.columns),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_duration_seconds": round(time.perf_counter() - pipeline_start, 1),
        "quick_mode": quick,
        "dataset_analysis": analysis,
        "all_model_results": {name: {k: v for k, v in m.items() if k not in ("roc_curve", "pr_curve")} for name, m in results.items()},
        "validation_results": {name: {k: v for k, v in m.items() if k not in ("roc_curve", "pr_curve")} for name, m in val_results.items()},
        "selected_model": best_name,
        "label_encoder_used": False,
    }
    with open(settings.MODEL_DIR / settings.METRICS_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Artifacts saved to {}", settings.MODEL_DIR)

    # 8. Register in Postgres — deactivate any previous active model
    db = SessionLocal()
    try:
        db.query(ModelRegistry).filter(ModelRegistry.status == ModelStatus.ACTIVE).update(
            {"status": ModelStatus.INACTIVE}
        )

        hyperparameters = None
        if hasattr(best_model, "get_params"):
            try:
                hyperparameters = {k: v for k, v in best_model.get_params().items() if v is None or isinstance(v, (str, int, float, bool))}
            except Exception:  # noqa: BLE001
                hyperparameters = None

        registry_entry = ModelRegistry(
            version=version,
            algorithm=best_name,
            status=ModelStatus.ACTIVE,
            accuracy=best_metrics["accuracy"],
            precision=best_metrics["precision"],
            recall=best_metrics["recall"],
            f1_score=best_metrics["f1_score"],
            roc_auc=best_metrics["roc_auc"],
            pr_auc=best_metrics["pr_auc"],
            training_date=datetime.now(timezone.utc),
            dataset_name="creditcard.csv (ULB Credit Card Fraud Detection)",
            dataset_row_count=analysis["total_transactions"],
            model_file_path=str(settings.MODEL_DIR / settings.MODEL_FILE),
            scaler_file_path=str(settings.MODEL_DIR / settings.SCALER_FILE),
            shap_explainer_file_path=str(settings.MODEL_DIR / settings.SHAP_EXPLAINER_FILE),
            hyperparameters=hyperparameters,
        )
        db.add(registry_entry)
        db.commit()
        logger.info("Model registered in database | version={} status=ACTIVE", version)
    except Exception:
        db.rollback()
        logger.error(
            "Artifacts were saved to disk successfully, but registering the model in "
            "Postgres failed. The API will not be able to find this model via the "
            "database until this is resolved."
        )
        raise
    finally:
        db.close()

    total_time = time.perf_counter() - pipeline_start
    logger.info("=" * 70)
    logger.info("Training pipeline complete in {:.1f}s. Selected model: {}", total_time, best_name)
    logger.info("Recall={:.4f}  F1={:.4f}  Precision={:.4f}  ROC-AUC={:.4f}  Accuracy={:.4f}",
                best_metrics["recall"], best_metrics["f1_score"], best_metrics["precision"],
                best_metrics["roc_auc"], best_metrics["accuracy"])
    logger.info("=" * 70)

    return metadata
