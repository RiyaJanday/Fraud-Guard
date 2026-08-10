"""
CLI entry point for the FraudGuard training pipeline.

    python train_model.py             # full hyperparameter search (slower, best quality)
    python train_model.py --quick     # fixed hyperparameters, much faster (good for a first run)

The actual pipeline (load -> preprocess -> SMOTE -> train 3 candidates ->
evaluate -> select best -> SHAP -> save artifacts -> register in Postgres)
lives in app/services/training_service.py:run_training(), which this script
just calls and prints a summary of. That extraction exists so the exact
same logic is also callable from the admin-triggered POST /model/retrain
API endpoint (see api/v1/model.py) without maintaining two copies that
could drift apart — this file's only remaining job is being a nice CLI.
"""

import argparse
import sys

from app.core.exceptions import AppException
from app.core.logging import configure_logging, logger
from app.services.training_service import run_training


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the FraudGuard fraud detection model.")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Skip hyperparameter search, use fixed reasonable defaults (much faster, slightly lower quality).",
    )
    args = parser.parse_args()

    configure_logging()

    logger.info("=" * 70)
    logger.info("FraudGuard Model Training Pipeline {}", "(quick mode)" if args.quick else "(full hyperparameter search)")
    logger.info("=" * 70)

    try:
        metadata = run_training(quick=args.quick)
    except AppException as exc:
        logger.error(str(exc.message))
        sys.exit(1)

    best_name = metadata["selected_model"]
    best_metrics = metadata["all_model_results"][best_name]
    logger.info(
        "Done. Selected {} | recall={:.4f} f1={:.4f} precision={:.4f} roc_auc={:.4f} accuracy={:.4f}",
        best_name, best_metrics["recall"], best_metrics["f1_score"],
        best_metrics["precision"], best_metrics["roc_auc"], best_metrics["accuracy"],
    )


if __name__ == "__main__":
    main()
