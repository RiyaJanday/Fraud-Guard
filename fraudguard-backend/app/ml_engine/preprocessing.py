"""
Dataset loading, validation, analysis, feature engineering, and splitting for
the ULB Credit Card Fraud Detection dataset.

Every function here is defensive about the dataset's actual shape rather than
assuming it — per project requirements, we analyze creditcard.csv rather than
hardcoding assumptions about it, and we NEVER fabricate synthetic data if the
real dataset is missing.
"""

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from app.core.config import get_settings
from app.core.exceptions import DatasetNotFoundException, ValidationException
from app.core.logging import logger

settings = get_settings()

# The ULB dataset's known schema. Validated against, never assumed blindly.
REQUIRED_COLUMNS = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount", "Class"]

# Model input features: V1-V28 (already PCA-transformed/anonymized in the
# source dataset) plus engineered features derived from Amount and Time.
# Raw Time is deliberately excluded in favor of the cyclical `Hour` feature
# (see engineer_features) — Time is just seconds-elapsed-since-first-transaction
# in this dataset, which has no generalizable meaning beyond hour-of-day.
FEATURE_COLUMNS = [f"V{i}" for i in range(1, 29)] + ["Amount", "Amount_log", "Hour"]


def load_dataset(path: Optional[Path] = None) -> pd.DataFrame:
    """
    Loads creditcard.csv from the project root (or an explicit path, mainly
    for testing). Raises DatasetNotFoundException with a clear, actionable
    message if it's missing — never generates synthetic data as a fallback.
    """
    dataset_path = path or settings.DATASET_PATH
    if not dataset_path.exists():
        raise DatasetNotFoundException(
            f"Dataset not found at {dataset_path}. This project requires the real "
            "ULB Credit Card Fraud Detection dataset (creditcard.csv), available at "
            "https://www.kaggle.com/mlg-ulb/creditcardfraud — place it at the "
            "project root (one level above fraudguard-backend/). Synthetic data is "
            "never generated as a substitute."
        )

    logger.info("Loading dataset from {}", dataset_path)
    df = pd.read_csv(dataset_path)
    logger.info("Loaded {} rows, {} columns", len(df), df.shape[1])

    # The source CSV stores Class as a quoted string ("0"/"1") — coerce to int
    # defensively rather than assuming pandas inferred it correctly.
    df["Class"] = pd.to_numeric(df["Class"], errors="coerce")
    if df["Class"].isnull().any():
        raise ValidationException(
            "The Class column contains values that could not be parsed as numbers."
        )
    df["Class"] = df["Class"].astype(int)

    return df


def validate_dataset(df: pd.DataFrame) -> None:
    """Confirms the loaded CSV actually matches the expected ULB schema before proceeding."""
    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValidationException(
            f"Dataset is missing required columns: {missing_cols}. Expected the "
            f"ULB Credit Card Fraud dataset schema: {REQUIRED_COLUMNS}."
        )

    unique_classes = set(df["Class"].unique())
    if not unique_classes.issubset({0, 1}):
        raise ValidationException(
            f"Class column must be binary (0 = legitimate, 1 = fraud). Found: {unique_classes}"
        )

    if len(df) == 0:
        raise ValidationException("Dataset is empty.")

    logger.info("Dataset schema validated successfully.")


def analyze_dataset(df: pd.DataFrame) -> dict:
    """
    Real, computed analysis of the dataset — not assumed numbers. Logged and
    saved into metrics.json so the training run is fully auditable later.
    """
    total = len(df)
    class_counts = df["Class"].value_counts().to_dict()
    fraud_count = int(class_counts.get(1, 0))
    legit_count = int(class_counts.get(0, 0))

    analysis = {
        "total_transactions": total,
        "total_features": df.shape[1] - 1,  # exclude Class
        "legit_count": legit_count,
        "fraud_count": fraud_count,
        "fraud_percentage": round(fraud_count / total * 100, 4) if total else 0.0,
        "missing_values_total": int(df.isnull().sum().sum()),
        "columns": list(df.columns),
        "amount_stats": {
            "min": float(df["Amount"].min()),
            "max": float(df["Amount"].max()),
            "mean": float(df["Amount"].mean()),
            "median": float(df["Amount"].median()),
            "std": float(df["Amount"].std()),
        },
        "time_span_hours": round((df["Time"].max() - df["Time"].min()) / 3600, 2),
    }

    logger.info(
        "Dataset analysis | total={} fraud={} ({}%) legit={} missing_values={}",
        total, fraud_count, analysis["fraud_percentage"], legit_count, analysis["missing_values_total"],
    )
    return analysis


def handle_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Defensive imputation — the ULB dataset is known to have zero missing
    values, but we check rather than assume, and impute numeric columns with
    the median (robust to outliers, which fraud data is full of) if any
    ever show up.
    """
    missing = df.isnull().sum()
    missing_cols = missing[missing > 0]
    if missing_cols.empty:
        logger.info("No missing values detected.")
        return df

    logger.warning("Missing values detected, imputing with median: {}", missing_cols.to_dict())
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derives two features from raw columns rather than fabricating new data:
      - Hour: cyclical hour-of-day from Time (seconds elapsed), 0-23.
              Fraud is well known to cluster at certain hours; Time's raw
              absolute value doesn't generalize past this dataset's ~2-day
              window, but hour-of-day does.
      - Amount_log: log1p(Amount). Transaction amounts are heavily
              right-skewed (a few very large transactions dominate the raw
              scale); log-transforming compresses that range and typically
              helps linear/tree-based models split more evenly.
    """
    df = df.copy()
    df["Hour"] = (df["Time"] // 3600) % 24
    df["Amount_log"] = np.log1p(df["Amount"])
    return df


def split_features_target(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[FEATURE_COLUMNS].copy()
    y = df["Class"].copy()
    return X, y


def train_val_test_split(
    X: pd.DataFrame,
    y: pd.Series,
    test_size: float = 0.15,
    val_size: float = 0.15,
    random_state: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
    """
    Stratified 70/15/15 train/val/test split by default — stratification
    matters enormously here, since a random split could otherwise leave the
    test set with very few (or zero) fraud examples given how rare they are.
    """
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=test_size, stratify=y, random_state=random_state
    )
    val_relative_size = val_size / (1 - test_size)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=val_relative_size, stratify=y_temp, random_state=random_state
    )
    return X_train, X_val, X_test, y_train, y_val, y_test


def scale_features(
    X_train: pd.DataFrame, X_val: pd.DataFrame, X_test: pd.DataFrame
) -> tuple[StandardScaler, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Fits StandardScaler on TRAIN ONLY, then applies it to val/test — fitting
    on the full dataset (or worse, on val/test) would leak information about
    their distribution into training, inflating evaluation metrics.
    """
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(scaler.fit_transform(X_train), columns=X_train.columns, index=X_train.index)
    X_val_scaled = pd.DataFrame(scaler.transform(X_val), columns=X_val.columns, index=X_val.index)
    X_test_scaled = pd.DataFrame(scaler.transform(X_test), columns=X_test.columns, index=X_test.index)
    return scaler, X_train_scaled, X_val_scaled, X_test_scaled


def apply_smote(
    X_train: pd.DataFrame, y_train: pd.Series, sampling_strategy: float = 0.1, random_state: int = 42
) -> tuple[pd.DataFrame, pd.Series]:
    """
    Balances the TRAINING set only (never val/test — those must reflect
    real-world class distribution for evaluation to mean anything).

    sampling_strategy=0.1 (fraud becomes 10% of the training set, not a full
    1:1 balance) is a deliberate choice, not the SMOTE default:
      - A full 1:1 balance on this dataset would synthesize ~284k fake fraud
        rows from only ~340 real training examples, which risks generating
        highly repetitive, unrealistic synthetic patterns (over-fitting to
        SMOTE's own interpolation artifacts rather than real fraud behavior).
      - It also makes hyperparameter search (RandomizedSearchCV, run multiple
        times across 3 candidate models) computationally impractical on a
        typical laptop.
      - 10% still gives every model dramatically more fraud signal to learn
        from than the raw ~0.17% ratio, while keeping training set size and
        synthetic-to-real ratio sane. This is imported directly from
        imbalanced-learn per the project's SMOTE requirement.
    """
    fraud_count = int(y_train.sum())
    legit_count = len(y_train) - fraud_count
    logger.info("Before SMOTE | legit={} fraud={} ({}%)", legit_count, fraud_count, round(fraud_count / len(y_train) * 100, 3))

    from imblearn.over_sampling import SMOTE

    smote = SMOTE(sampling_strategy=sampling_strategy, random_state=random_state, k_neighbors=5)
    X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

    new_fraud = int((y_resampled == 1).sum())
    new_legit = int((y_resampled == 0).sum())
    logger.info("After SMOTE | legit={} fraud={} ({}%)", new_legit, new_fraud, round(new_fraud / len(y_resampled) * 100, 3))

    return X_resampled, y_resampled
