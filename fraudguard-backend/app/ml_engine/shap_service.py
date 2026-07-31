"""
SHAP explainability — builds an explainer for the winning model and turns
its output into both structured top-feature data and a natural-language
explanation.

Feature labels for V1-V28 are honest about what they are: anonymized PCA
components with no disclosed real-world meaning (per the dataset's own
documentation). We never fabricate a false business meaning for them (e.g.
claiming "V17 = merchant category") — that would be misinformation. Amount
and Hour, which ARE real un-anonymized fields, get real semantic labels.
"""

from typing import Optional

from app.core.logging import logger

FEATURE_LABELS = {
    "Amount": "Transaction amount",
    "Amount_log": "Transaction amount (log-scaled)",
    "Hour": "Hour of day the transaction occurred",
    **{f"V{i}": f"Anonymized transaction pattern V{i} (PCA component)" for i in range(1, 29)},
}


def build_explainer(model, background_sample):
    """
    shap.Explainer's unified API auto-selects the right algorithm under the
    hood (TreeExplainer for RandomForest/XGBoost, LinearExplainer for
    LogisticRegression, etc.) based on the model type passed in — so this
    works regardless of which of the 3 candidate models wins.

    `background_sample` should be a small sample (not the full training set)
    — SHAP uses it as a reference distribution, and a few hundred rows is
    plenty while keeping explainer construction fast.
    """
    import shap

    logger.info("Building SHAP explainer ({} background rows)...", len(background_sample))
    explainer = shap.Explainer(model, background_sample)
    logger.info("SHAP explainer built.")
    return explainer


def explain_instance(explainer, X_row, top_n: int = 5) -> list[dict]:
    """
    Returns the top_n features driving this single prediction, sorted by
    |impact| descending. X_row must be a single-row DataFrame with the same
    columns (and same scaling) the model was trained on.
    """
    shap_values = explainer(X_row)
    values = shap_values.values[0]

    # Some SHAP explainer/model combinations return shape (n_features, n_classes)
    # for a single row instead of (n_features,) — normalize to a flat 1D array
    # representing the positive (fraud) class's contribution.
    if hasattr(values, "ndim") and values.ndim > 1:
        values = values[:, 1] if values.shape[-1] == 2 else values.ravel()

    feature_names = list(X_row.columns)
    pairs = sorted(zip(feature_names, values), key=lambda p: abs(p[1]), reverse=True)[:top_n]

    return [
        {
            "feature": name,
            "label": FEATURE_LABELS.get(name, name),
            "impact": round(float(val), 4),
            "value": round(float(X_row[name].iloc[0]), 4),
        }
        for name, val in pairs
    ]


def generate_explanation(top_features: list[dict], is_fraud: bool, risk_score: float) -> str:
    """Turns structured SHAP output into a short natural-language explanation."""
    if not top_features:
        return (
            f"This transaction scored {risk_score:.0f}/100. No dominant risk factors "
            f"were identified — the decision reflects the combined effect of many small signals."
        )

    positive_drivers = [f for f in top_features if f["impact"] > 0]
    driver_labels = [f["label"] for f in (positive_drivers or top_features)[:3]]
    driver_text = ", ".join(driver_labels)

    if is_fraud:
        return (
            f"This transaction was flagged as high risk (score {risk_score:.0f}/100), "
            f"primarily driven by: {driver_text}. These signals deviated significantly "
            f"from the patterns the model learned from legitimate transactions."
        )
    return (
        f"This transaction scored low risk (score {risk_score:.0f}/100). The strongest "
        f"contributing signals were: {driver_text}, consistent with typical legitimate "
        f"transaction behavior."
    )
