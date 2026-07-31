"""
Standalone training pipeline for the FraudGuard fraud-detection model.

Run from the fraudguard-backend/ directory:

    python train_model.py             # full hyperparameter search (slower, best quality)
    python train_model.py --quick     # fixed hyperparameters, much faster (good for a first run)

Loads creditcard.csv from the project root (one level up), analyzes it,
engineers features, splits it (stratified 70/15/15 train/val/test), balances
the training set with SMOTE, trains Logistic Regression / Random Forest /
XGBoost, evaluates all three on the untouched test set, and saves whichever
wins by Recall > F1 > Precision > ROC-AUC > Accuracy priority. Registers the
winning model in the model_registry table as ACTIVE (deactivating any
previous active model), so the FastAPI inference service and future
/metrics endpoints can find it.

Never retrains during inference — this script is the ONLY place training
happens. app/ml_engine/predictor.py only ever loads what this script saves.
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

import joblib

from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging, logger
from app.database.session import SessionLocal
from app.ml_engine import evaluation, preprocessing, shap_service, training
from app.models.model_registry import ModelRegistry, ModelStatus


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the FraudGuard fraud detection model.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip hyperparameter search, use fixed reasonable defaults (much faster, slightly lower quality).",
    )
    args = parser.parse_args()

    configure_logging()
    settings = get_settings()

    logger.info("=" * 70)
    logger.info("FraudGuard Model Training Pipeline {}", "(quick mode)" if args.quick else "(full hyperparameter search)")
    logger.info("=" * 70)

    pipeline_start = time.perf_counter()

    # ------------------------------------------------------------------ #
    # 1. Load + validate + analyze
    # ------------------------------------------------------------------ #
    try:
        df = preprocessing.load_dataset()
    except AppException as exc:
        logger.error(str(exc.message))
        sys.exit(1)

    preprocessing.validate_dataset(df)
    analysis = preprocessing.analyze_dataset(df)
    logger.info("Dataset analysis:\n{}", json.dumps(analysis, indent=2))

    # ------------------------------------------------------------------ #
    # 2. Preprocess + engineer features
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # 3. Train all 3 candidates
    # ------------------------------------------------------------------ #
    models = {}

    t0 = time.perf_counter()
    logger.info("Training Logistic Regression...")
    models["logistic_regression"] = training.train_logistic_regression(X_train_res, y_train_res, quick=args.quick)
    logger.info("  done in {:.1f}s", time.perf_counter() - t0)

    t0 = time.perf_counter()
    logger.info("Training Random Forest...")
    models["random_forest"] = training.train_random_forest(X_train_res, y_train_res, quick=args.quick)
    logger.info("  done in {:.1f}s", time.perf_counter() - t0)

    t0 = time.perf_counter()
    logger.info("Training XGBoost...")
    models["xgboost"] = training.train_xgboost(X_train_res, y_train_res, quick=args.quick)
    logger.info("  done in {:.1f}s", time.perf_counter() - t0)

    # ------------------------------------------------------------------ #
    # 4. Evaluate all 3 on the held-out TEST set (never touched until now)
    # ------------------------------------------------------------------ #
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

    # Also log validation-set performance for transparency, even though
    # model selection is decided on the test set exclusively.
    val_results = {name: evaluation.evaluate_model(model, X_val_scaled, y_val) for name, model in models.items()}
    logger.info("(Validation-set metrics, for reference only — selection uses test set)")
    for name, metrics in val_results.items():
        logger.info(
            "  {:20s} | acc={:.4f} prec={:.4f} recall={:.4f} f1={:.4f}",
            name, metrics["accuracy"], metrics["precision"], metrics["recall"], metrics["f1_score"],
        )

    # ------------------------------------------------------------------ #
    # 5. Select best model — Recall > F1 > Precision > ROC-AUC > Accuracy
    # ------------------------------------------------------------------ #
    best_name = evaluation.select_best_model(results)
    best_model = models[best_name]
    best_metrics = results[best_name]

    # ------------------------------------------------------------------ #
    # 6. Build SHAP explainer (on a small background sample, not the full set)
    # ------------------------------------------------------------------ #
    background = X_train_res.sample(n=min(200, len(X_train_res)), random_state=42)
    explainer = shap_service.build_explainer(best_model, background)

    # ------------------------------------------------------------------ #
    # 7. Save artifacts
    # ------------------------------------------------------------------ #
    settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, settings.MODEL_DIR / settings.MODEL_FILE)
    joblib.dump(scaler, settings.MODEL_DIR / settings.SCALER_FILE)
    joblib.dump(explainer, settings.MODEL_DIR / settings.SHAP_EXPLAINER_FILE)
    # No label_encoder.joblib: Class arrives already binary/numeric in this
    # dataset, so label encoding is genuinely not required (not skipped for
    # convenience — see preprocessing.load_dataset's Class coercion).

    version = f"v{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    metadata = {
        "model_version": version,
        "algorithm": best_name,
        "feature_columns": list(X_train.columns),
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_duration_seconds": round(time.perf_counter() - pipeline_start, 1),
        "quick_mode": args.quick,
        "dataset_analysis": analysis,
        "all_model_results": {name: {k: v for k, v in m.items() if k not in ("roc_curve", "pr_curve")} for name, m in results.items()},
        "validation_results": {name: {k: v for k, v in m.items() if k not in ("roc_curve", "pr_curve")} for name, m in val_results.items()},
        "selected_model": best_name,
        "label_encoder_used": False,
    }
    with open(settings.MODEL_DIR / settings.METRICS_FILE, "w") as f:
        json.dump(metadata, f, indent=2)

    logger.info("Artifacts saved to {}", settings.MODEL_DIR)
    logger.info("  - {}", settings.MODEL_FILE)
    logger.info("  - {}", settings.SCALER_FILE)
    logger.info("  - {}", settings.SHAP_EXPLAINER_FILE)
    logger.info("  - {}", settings.METRICS_FILE)

    # ------------------------------------------------------------------ #
    # 8. Register in Postgres — deactivate any previous active model
    # ------------------------------------------------------------------ #
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
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error(
            "Artifacts were saved to disk successfully, but registering the model in "
            "Postgres failed: {}. The API will not be able to find this model via the "
            "database until this is resolved (check DATABASE_URL / that migrations have "
            "been applied).", exc,
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


if __name__ == "__main__":
    main()
