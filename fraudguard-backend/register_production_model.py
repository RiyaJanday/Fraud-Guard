"""
One-off script: register the locally-trained model in a REMOTE (production)
database's model_registry table, without re-running training there.

Why this is needed: the deployed backend image ships the already-trained
.joblib artifacts (see DEPLOYMENT.md), so /predict works fine on Render.
But train_model.py — the only place that writes a model_registry row — was
only ever run against your LOCAL dev database, never Render's Postgres.
Without an ACTIVE row there, the Dashboard's "Model Performance" radar and
"Detection Accuracy" stat have nothing to read and fall back to zero, even
though SHAP/scoring (which reads live prediction data, not model_registry)
works correctly.

Usage:
    cd fraudguard-backend
    python register_production_model.py --database-url "postgresql+psycopg2://user:pass@host/db"

Getting --database-url:
    Render dashboard -> your Postgres service -> Connect -> "External
    Database URL". Render gives you a plain postgresql:// URL — change the
    scheme to postgresql+psycopg2:// before passing it here (same swap
    DEPLOYMENT.md already has you do for the backend's own DATABASE_URL env
    var). Must be the EXTERNAL url (not internal) since you're running this
    from your own machine, not from inside Render's network.

Safe to re-run: deactivates any existing ACTIVE row first, exactly like
train_model.py's own registration step does. If this exact model_version is
already registered, it reactivates and refreshes that row instead of
creating a duplicate.
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.model_registry import ModelRegistry, ModelStatus

METRICS_PATH = Path(__file__).parent / "app" / "ml_engine" / "models" / "metrics.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Register the local trained model in a remote database.")
    parser.add_argument(
        "--database-url",
        required=True,
        help="Full postgresql+psycopg2:// URL for the target (production) database",
    )
    args = parser.parse_args()

    if not METRICS_PATH.exists():
        raise SystemExit(f"metrics.json not found at {METRICS_PATH} — run train_model.py locally first.")

    with open(METRICS_PATH) as f:
        metadata = json.load(f)

    best_name = metadata["selected_model"]
    best_metrics = metadata["all_model_results"][best_name]
    version = metadata["model_version"]

    engine = create_engine(args.database_url, connect_args={"options": "-c timezone=utc"})
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Deactivate any currently-active model — mirrors train_model.py.
        db.query(ModelRegistry).filter(ModelRegistry.status == ModelStatus.ACTIVE).update(
            {"status": ModelStatus.INACTIVE}
        )

        existing = db.query(ModelRegistry).filter(ModelRegistry.version == version).first()
        if existing:
            print(f"Version {version} already registered (id={existing.id}) — reactivating instead of duplicating.")
            existing.status = ModelStatus.ACTIVE
            existing.accuracy = best_metrics["accuracy"]
            existing.precision = best_metrics["precision"]
            existing.recall = best_metrics["recall"]
            existing.f1_score = best_metrics["f1_score"]
            existing.roc_auc = best_metrics["roc_auc"]
            existing.pr_auc = best_metrics["pr_auc"]
        else:
            entry = ModelRegistry(
                version=version,
                algorithm=best_name,
                status=ModelStatus.ACTIVE,
                accuracy=best_metrics["accuracy"],
                precision=best_metrics["precision"],
                recall=best_metrics["recall"],
                f1_score=best_metrics["f1_score"],
                roc_auc=best_metrics["roc_auc"],
                pr_auc=best_metrics["pr_auc"],
                training_date=datetime.fromisoformat(metadata["trained_at"]),
                dataset_name="creditcard.csv (ULB Credit Card Fraud Detection)",
                dataset_row_count=metadata["dataset_analysis"]["total_transactions"],
                model_file_path="app/ml_engine/models/model.joblib",
                scaler_file_path="app/ml_engine/models/scaler.joblib",
                shap_explainer_file_path="app/ml_engine/models/shap_explainer.joblib",
                hyperparameters=None,
                notes=(
                    "Registered post-deploy from local metrics.json — train_model.py ran "
                    "locally, artifacts shipped via the Docker image; see "
                    "register_production_model.py."
                ),
            )
            db.add(entry)

        db.commit()
        print(f"Model {version} ({best_name}) is now ACTIVE.")
        print(
            f"  accuracy={best_metrics['accuracy']:.4f} precision={best_metrics['precision']:.4f} "
            f"recall={best_metrics['recall']:.4f} f1={best_metrics['f1_score']:.4f} "
            f"roc_auc={best_metrics['roc_auc']:.4f} pr_auc={best_metrics['pr_auc']:.4f}"
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
