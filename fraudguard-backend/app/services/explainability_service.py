"""
Business logic for the global model-explainability view.

Two real, non-fabricated signals compose this endpoint:

1. Model card — pulled straight from ModelRegistry + the latest ModelMetrics
   snapshot (confusion matrix included, when train_model.py recorded one).
2. Global feature importance — NOT re-derived from the raw model object
   (which would need to be loaded and re-run here, duplicating
   predictor.py's job). Instead, this aggregates the REAL, already-computed
   SHAP output stored on each FraudPrediction row (top_shap_features) across
   a recent sample of real scored transactions. Each prediction only stores
   its top 5 SHAP features (see shap_service.py) — not all 31 — so a
   feature's `sample_count` here means "how often it appeared in some
   transaction's top 5", and `avg_impact` is its average |SHAP value| across
   those specific appearances. That's an honest, real-data-driven summary,
   distinct from (but a legitimate proxy for) the model's true global
   feature_importances_.
"""

from collections import defaultdict

from sqlalchemy.orm import Session

from app.repositories.fraud_prediction_repository import FraudPredictionRepository
from app.repositories.model_registry_repository import ModelRegistryRepository
from app.schemas.explainability import (
    ConfusionMatrixOut,
    ExplainabilityOut,
    FeatureImportanceOut,
    ModelInfoOut,
    RecentExplanationOut,
)
from app.schemas.transaction import ShapFeatureOut

_GLOBAL_SAMPLE_SIZE = 200
_RECENT_EXAMPLES_LIMIT = 5
_TOP_FEATURES_LIMIT = 10


class ExplainabilityService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.predictions = FraudPredictionRepository(db)
        self.model_registry = ModelRegistryRepository(db)

    def get_explainability(self) -> ExplainabilityOut:
        active_model = self.model_registry.get_active()
        model_info = None
        if active_model:
            latest_metrics = self.model_registry.get_latest_metrics(active_model.id)
            model_info = ModelInfoOut(
                version=active_model.version,
                algorithm=active_model.algorithm,
                status=active_model.status.value,
                accuracy=active_model.accuracy,
                precision=active_model.precision,
                recall=active_model.recall,
                f1_score=active_model.f1_score,
                roc_auc=active_model.roc_auc,
                pr_auc=active_model.pr_auc,
                training_date=active_model.training_date,
                dataset_name=active_model.dataset_name,
                dataset_row_count=active_model.dataset_row_count,
                confusion_matrix=ConfusionMatrixOut(**latest_metrics.confusion_matrix) if latest_metrics else None,
            )

        sample = self.predictions.list_recent(limit=_GLOBAL_SAMPLE_SIZE)
        importance = self._aggregate_feature_importance(sample)

        recent = self.predictions.list_recent(limit=_RECENT_EXAMPLES_LIMIT, high_risk_only=True)
        recent_out = [
            RecentExplanationOut(
                transaction_id=pred.transaction_id,
                merchant=pred.transaction.merchant if pred.transaction else None,
                amount=pred.transaction.amount if pred.transaction else 0.0,
                currency=pred.transaction.currency if pred.transaction else "INR",
                risk_score=pred.risk_score,
                decision=pred.decision,
                explanation=pred.explanation,
                top_shap_features=[ShapFeatureOut(**f) for f in pred.top_shap_features],
                created_at=pred.created_at,
            )
            for pred in recent
        ]

        return ExplainabilityOut(
            model=model_info,
            global_feature_importance=importance,
            recent_explanations=recent_out,
            sample_size=len(sample),
        )

    @staticmethod
    def _aggregate_feature_importance(predictions) -> list[FeatureImportanceOut]:
        impact_sum: dict[str, float] = defaultdict(float)
        count: dict[str, int] = defaultdict(int)
        label_for: dict[str, str] = {}

        for pred in predictions:
            for f in pred.top_shap_features or []:
                feature = f.get("feature")
                if not feature:
                    continue
                impact_sum[feature] += abs(f.get("impact", 0.0))
                count[feature] += 1
                label_for[feature] = f.get("label", feature)

        ranked = sorted(impact_sum.keys(), key=lambda k: impact_sum[k] / count[k], reverse=True)
        return [
            FeatureImportanceOut(
                feature=feature,
                label=label_for[feature],
                avg_impact=round(impact_sum[feature] / count[feature], 4),
                sample_count=count[feature],
            )
            for feature in ranked[:_TOP_FEATURES_LIMIT]
        ]
