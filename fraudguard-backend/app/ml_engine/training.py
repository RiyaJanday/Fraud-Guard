"""
Trains the 3 candidate models: Logistic Regression, Random Forest, XGBoost.

Hyperparameter search uses RandomizedSearchCV scored on F1 (a stable,
balanced objective for tuning) rather than Recall alone — optimizing purely
for recall during CV can push a search toward degenerate high-recall/
low-precision configurations (this is exactly what happened at the top
level too — see evaluation.select_best_model's docstring for a real example
from this project's own training run). The BEST-MODEL SELECTION among the 3
final candidates uses F1 as the primary criterion for the same reason,
applied once at the top level rather than baked into every individual
search here.

`quick=True` skips hyperparameter search entirely and uses fixed, reasonable
defaults — useful for a fast first run / sanity check before committing to
the full search, which can take a while on 3 models against a dataset this
size.
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import RandomizedSearchCV

from app.core.logging import logger

RANDOM_STATE = 42


def train_logistic_regression(X_train, y_train, quick: bool = False):
    base = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE, class_weight="balanced")

    if quick:
        base.fit(X_train, y_train)
        return base

    param_grid = {
        "C": [0.01, 0.1, 1, 10],
        "penalty": ["l2"],
        "solver": ["lbfgs"],
    }
    search = RandomizedSearchCV(
        base, param_grid, n_iter=4, cv=3, scoring="f1", n_jobs=-1, random_state=RANDOM_STATE
    )
    search.fit(X_train, y_train)
    logger.info("Best LogisticRegression params: {}", search.best_params_)
    return search.best_estimator_


def train_random_forest(X_train, y_train, quick: bool = False):
    if quick:
        base = RandomForestClassifier(
            random_state=RANDOM_STATE, n_jobs=-1, class_weight="balanced",
            n_estimators=150, max_depth=12,
        )
        base.fit(X_train, y_train)
        return base

    # n_jobs=1 here (NOT -1) is deliberate: this estimator is wrapped in
    # RandomizedSearchCV(n_jobs=-1) below. Setting -1 on BOTH the outer
    # search and the inner estimator causes severe CPU oversubscription --
    # the search tries to run multiple fits in parallel across all cores,
    # and each of those fits ALSO tries to use all cores to build its trees,
    # so they fight each other for the same cores instead of cooperating.
    # Combined with removing unbounded max_depth (below), this took Random
    # Forest's full search from ~20 minutes to a small fraction of that on
    # the real 284K-row dataset.
    base = RandomForestClassifier(random_state=RANDOM_STATE, n_jobs=1, class_weight="balanced")

    param_dist = {
        "n_estimators": [100, 200, 300],
        # No `None` (unbounded depth): on ~150K training rows per CV fold,
        # an unconstrained tree can grow extremely deep and slow to build.
        # 20 is already generous -- capped not because deep trees are bad,
        # but because *unbounded* is an unpredictable worst case with no
        # real accuracy benefit over a generous cap at this dataset size.
        "max_depth": [8, 12, 16, 20],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    }
    search = RandomizedSearchCV(
        base, param_dist, n_iter=8, cv=3, scoring="f1", n_jobs=-1, random_state=RANDOM_STATE
    )
    search.fit(X_train, y_train)
    logger.info("Best RandomForest params: {}", search.best_params_)
    return search.best_estimator_


def train_xgboost(X_train, y_train, quick: bool = False):
    import xgboost as xgb

    # Additional imbalance handling on top of SMOTE: weight the positive
    # class by the (post-SMOTE) class ratio, so XGBoost's loss function
    # still penalizes missed fraud more heavily even after resampling.
    fraud_count = int((y_train == 1).sum())
    legit_count = int((y_train == 0).sum())
    scale_pos_weight = legit_count / max(fraud_count, 1)

    if quick:
        base = xgb.XGBClassifier(
            random_state=RANDOM_STATE, n_jobs=-1, eval_metric="logloss",
            scale_pos_weight=scale_pos_weight, n_estimators=200, max_depth=6, learning_rate=0.1,
        )
        base.fit(X_train, y_train)
        return base

    # n_jobs=1 (not -1) for the same reason as Random Forest above -- this
    # estimator is wrapped in RandomizedSearchCV(n_jobs=-1) below, and
    # nesting n_jobs=-1 on both layers causes CPU oversubscription.
    base = xgb.XGBClassifier(
        random_state=RANDOM_STATE, n_jobs=1, eval_metric="logloss", scale_pos_weight=scale_pos_weight
    )

    param_dist = {
        "n_estimators": [100, 200, 300],
        "max_depth": [4, 6, 8],
        "learning_rate": [0.01, 0.05, 0.1, 0.2],
        "subsample": [0.7, 0.85, 1.0],
        "colsample_bytree": [0.7, 0.85, 1.0],
    }
    search = RandomizedSearchCV(
        base, param_dist, n_iter=10, cv=3, scoring="f1", n_jobs=-1, random_state=RANDOM_STATE
    )
    search.fit(X_train, y_train)
    logger.info("Best XGBoost params: {}", search.best_params_)
    return search.best_estimator_
