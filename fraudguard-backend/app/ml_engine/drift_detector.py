"""
Data drift detection: compares the statistical distribution of recently
scored live transactions against the distribution of the original ULB
training dataset, using the two-sample Kolmogorov-Smirnov test per feature.

Reference distribution:
    Computed once from creditcard.csv (the exact same file train_model.py
    trains on) and cached to app/ml_engine/models/drift_reference.json.
    Re-reading and re-sampling a 284K-row CSV on every drift check would be
    needlessly slow for data that never changes between training runs.
    Delete that cache file (or retrain) to force a recompute — e.g. after
    swapping in an updated dataset.

Live distribution:
    Pulled directly from the `transactions` table via
    TransactionRepository.list_recent_features — the ACTUAL v_features and
    amount values submitted through /predict, not a synthetic sample.

Why the Kolmogorov-Smirnov test, not a simpler check like comparing means:
    A live feature could have an unchanged mean but a completely different
    shape (e.g. a shift from unimodal to bimodal) — exactly the kind of
    drift that matters most in a PCA-transformed feature space, where "mean"
    alone is not a very meaningful summary to begin with. KS is
    nonparametric (it assumes nothing about the feature being normally
    distributed, which V1-V28 are not) and directly compares the two
    empirical distributions rather than a single summary statistic of each.

A feature is flagged "drifted" when its two-sided KS test p-value < ALPHA
(0.05, the conventional significance threshold) — i.e., we can reject the
null hypothesis that the live and reference samples come from the same
distribution. Overall `drift_detected` only fires when MORE than
DRIFT_FEATURE_THRESHOLD (30%) of the 29 features are individually flagged:
running 29 independent hypothesis tests at alpha=0.05 will flag roughly 1-2
features by pure chance even with zero real drift (the multiple-comparisons
problem), so treating any single flagged feature as "drift detected" would
cry wolf on almost every check. Many features drifting together is the
actual signal worth surfacing.
"""

import json
from typing import Optional

from scipy.stats import ks_2samp

from app.core.config import get_settings
from app.core.logging import logger
from app.ml_engine.preprocessing import load_dataset

settings = get_settings()

ALPHA = 0.05
DRIFT_FEATURE_THRESHOLD = 0.3
MIN_SAMPLE_SIZE = 30  # below this, a KS test's p-value is too noisy to report responsibly
DRIFT_FEATURES = [f"V{i}" for i in range(1, 29)] + ["Amount"]

_REFERENCE_CACHE_PATH = settings.MODEL_DIR / "drift_reference.json"
_REFERENCE_SAMPLE_SIZE = 5000  # a random sample is statistically sufficient for KS and keeps the cache file small


def _build_reference_distribution() -> dict[str, list[float]]:
    df = load_dataset()
    sample = df.sample(n=min(_REFERENCE_SAMPLE_SIZE, len(df)), random_state=42)
    return {feature: sample[feature].tolist() for feature in DRIFT_FEATURES}


def _load_or_build_reference() -> dict[str, list[float]]:
    if _REFERENCE_CACHE_PATH.exists():
        try:
            with open(_REFERENCE_CACHE_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Drift reference cache unreadable ({}) — rebuilding.", exc)

    logger.info("Building drift reference distribution from {} (cache miss).", settings.DATASET_PATH)
    reference = _build_reference_distribution()
    _REFERENCE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_REFERENCE_CACHE_PATH, "w") as f:
        json.dump(reference, f)
    logger.info("Drift reference distribution cached to {}.", _REFERENCE_CACHE_PATH)
    return reference


def compute_drift_report(live_rows: list[dict]) -> dict:
    """
    live_rows: dicts each containing V1..V28 and Amount keys (see
    TransactionRepository.list_recent_features). Returns a JSON-serializable
    report — per-feature KS statistic/p-value/drifted flag, plus an overall
    summary — ready to hand straight to a Pydantic response schema.
    """
    if len(live_rows) < MIN_SAMPLE_SIZE:
        return {
            "status": "insufficient_data",
            "sample_size": len(live_rows),
            "minimum_required": MIN_SAMPLE_SIZE,
            "message": (
                f"Only {len(live_rows)} scored transactions available; at least "
                f"{MIN_SAMPLE_SIZE} are needed for a statistically meaningful drift check."
            ),
            "features": [],
            "drift_detected": False,
            "drifted_feature_count": 0,
            "total_feature_count": len(DRIFT_FEATURES),
            "drift_ratio": 0.0,
            "threshold": DRIFT_FEATURE_THRESHOLD,
        }

    reference = _load_or_build_reference()

    features_report = []
    drifted_count = 0
    for feature in DRIFT_FEATURES:
        live_values = [row[feature] for row in live_rows if row.get(feature) is not None]
        if len(live_values) < MIN_SAMPLE_SIZE:
            continue  # this specific feature has too many nulls in the live sample to test fairly

        statistic, p_value = ks_2samp(reference[feature], live_values)
        drifted = bool(p_value < ALPHA)
        if drifted:
            drifted_count += 1
        features_report.append(
            {
                "feature": feature,
                "ks_statistic": round(float(statistic), 4),
                "p_value": round(float(p_value), 4),
                "drifted": drifted,
            }
        )

    total_checked = len(features_report)
    drift_ratio = round(drifted_count / total_checked, 3) if total_checked else 0.0
    overall_drift = drift_ratio > DRIFT_FEATURE_THRESHOLD

    return {
        "status": "ok",
        "sample_size": len(live_rows),
        "features": sorted(features_report, key=lambda f: f["p_value"]),
        "drift_detected": overall_drift,
        "drifted_feature_count": drifted_count,
        "total_feature_count": total_checked,
        "drift_ratio": drift_ratio,
        "threshold": DRIFT_FEATURE_THRESHOLD,
    }
