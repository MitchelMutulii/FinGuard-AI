"""
anomaly_detector.py
-------------------

Unsupervised anomaly detection for FinGuard AI using IsolationForest.

- Expected input: pandas DataFrame with at least these columns:
    - "transaction_id" (optional, used for reference)
    - "date"           (string: YYYY-MM-DD)
    - "merchant"       (string)
    - "category"       (string)
    - "amount"         (float)

- Main functions:
    - train_anomaly_model(df, contamination=0.05)
    - score_transactions(model, df)
    - save_model(model, path)
    - load_model(path)

This module can be used offline to train a model, then loaded by the API
to flag suspicious transactions for a user or SME.
"""

from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline


# -------------------------------------------------------------------
# 1. Data schema + helper
# -------------------------------------------------------------------

REQUIRED_COLUMNS = ["date", "merchant", "category", "amount"]


def _ensure_required_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in DataFrame: {missing}")


def _add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Derive extra features to help the model:
      - day_of_week (0 = Monday ... 6 = Sunday)
    """
    df = df.copy()

    # Parse date if it is a string
    if not np.issubdtype(df["date"].dtype, np.datetime64):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["day_of_week"] = df["date"].dt.dayofweek

    # Replace NaNs in day_of_week with -1 (unknown)
    df["day_of_week"] = df["day_of_week"].fillna(-1).astype(int)

    return df


# -------------------------------------------------------------------
# 2. Model wrapper using dataclass
# -------------------------------------------------------------------

@dataclass
class AnomalyDetectionModel:
    """
    Wrapper holding the sklearn pipeline, so it can be saved/loaded easily.
    """
    pipeline: Pipeline
    contamination: float = 0.05  # expected fraction of anomalies


def build_preprocessing_and_model(contamination: float = 0.05) -> Pipeline:
    """
    Create a sklearn Pipeline that:
      - one-hot encodes categorical columns
      - passes numeric columns unchanged
      - fits IsolationForest for anomaly detection
    """
    numeric_features = ["amount", "day_of_week"]
    categorical_features = ["merchant", "category"]

    numeric_transformer = "passthrough"
    categorical_transformer = OneHotEncoder(handle_unknown="ignore")

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, numeric_features),
            ("cat", categorical_transformer, categorical_features),
        ]
    )

    isolation_forest = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", isolation_forest),
        ]
    )

    return pipeline


# -------------------------------------------------------------------
# 3. Training + scoring
# -------------------------------------------------------------------

def train_anomaly_model(
    df: pd.DataFrame,
    contamination: float = 0.05,
) -> AnomalyDetectionModel:
    """
    Train an IsolationForest-based anomaly detector.
    'contamination' controls the expected fraction of anomalies (0.01–0.10 typical).
    """
    _ensure_required_columns(df)
    df_feat = _add_derived_features(df)

    pipeline = build_preprocessing_and_model(contamination=contamination)

    # Use only the columns needed by the pipeline
    fit_df = df_feat[["merchant", "category", "amount", "day_of_week"]]

    pipeline.fit(fit_df)

    return AnomalyDetectionModel(pipeline=pipeline, contamination=contamination)


def score_transactions(
    model: AnomalyDetectionModel,
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Apply a fitted model to new transactions.
    Returns a copy of df with:
      - anomaly_score  (float, lower = more anomalous)
      - is_anomaly     (0 = normal, 1 = anomaly)
    """
    _ensure_required_columns(df)
    df_feat = _add_derived_features(df)

    X = df_feat[["merchant", "category", "amount", "day_of_week"]]

    # IsolationForest.decision_function: higher values = more normal
    # We'll invert it so higher = more suspicious, then normalize.
    raw_scores = model.pipeline.decision_function(X)  # shape (n_samples,)
    raw_scores = np.array(raw_scores)

    # Convert to a 0–1 anomaly score (1 = most suspicious)
    # We flip sign because IsolationForest uses negative scores as anomalies.
    flipped = -raw_scores
    # Normalize to 0–1
    if flipped.max() == flipped.min():
        norm_scores = np.zeros_like(flipped)
    else:
        norm_scores = (flipped - flipped.min()) / (flipped.max() - flipped.min())

    # Predict label: -1 = anomaly, 1 = normal
    labels = model.pipeline.predict(X)
    is_anomaly = (labels == -1).astype(int)

    result = df.copy()
    result["anomaly_score"] = norm_scores
    result["is_anomaly"] = is_anomaly

    return result


# -------------------------------------------------------------------
# 4. Save / load helpers
# -------------------------------------------------------------------

def save_model(model: AnomalyDetectionModel, path: str) -> None:
    """Save model to disk using pickle."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path: str) -> AnomalyDetectionModel:
    """Load model from disk."""
    with open(path, "rb") as f:
        model = pickle.load(f)
    if not isinstance(model, AnomalyDetectionModel):
        raise TypeError("Loaded object is not an AnomalyDetectionModel")
    return model


# -------------------------------------------------------------------
# 5. Standalone usage for quick local testing
# -------------------------------------------------------------------

def _generate_dummy_transactions(n: int = 200) -> pd.DataFrame:
    """
    Generate a synthetic transaction table for quick testing,
    if you don't have a CSV yet.
    """
    rng = np.random.default_rng(seed=42)

    merchants = ["Supermarket X", "Coffee Shop Z", "Online Store Y", "Taxi Co"]
    categories = ["Groceries", "Coffee", "Electronics", "Transport"]

    dates = pd.date_range("2025-12-01", periods=30, freq="D")
    rows = []
    tid = 1

    for _ in range(n):
        merchant = rng.choice(merchants)
        category = rng.choice(categories)
        date = rng.choice(dates)

        # Normal amounts vary by category
        base_amounts = {
            "Groceries": 1000,
            "Coffee": 250,
            "Electronics": 30000,
            "Transport": 500,
        }
        std_amounts = {
            "Groceries": 400,
            "Coffee": 80,
            "Electronics": 8000,
            "Transport": 200,
        }

        mean = base_amounts[category]
        std = std_amounts[category]
        amount = float(max(50, rng.normal(mean, std)))  # no negative amounts

        rows.append(
            {
                "transaction_id": tid,
                "date": date,
                "merchant": merchant,
                "category": category,
                "amount": round(amount, 2),
                "currency": "KES",
                "payment_method": "Card",
            }
        )
        tid += 1

    # Inject a few clear anomalies
    for _ in range(5):
        rows.append(
            {
                "transaction_id": tid,
                "date": rng.choice(dates),
                "merchant": "Unknown Merchant",
                "category": "Other",
                "amount": float(rng.uniform(60000, 150000)),
                "currency": "KES",
                "payment_method": "Card",
            }
        )
        tid += 1

    return pd.DataFrame(rows)


if __name__ == "__main__":
    """
    Quick local test:
      python src/backend/ml/anomaly_detector.py
    """
    print("Generating dummy transactions...")
    df = _generate_dummy_transactions(200)

    print("Training anomaly detection model...")
    model = train_anomaly_model(df, contamination=0.05)

    print("Scoring transactions...")
    scored = score_transactions(model, df)

    # Show top 10 most suspicious transactions
    top_suspicious = scored.sort_values("anomaly_score", ascending=False).head(10)
    print("\nTop 10 suspicious transactions:")
    print(top_suspicious[["transaction_id", "date", "merchant", "category", "amount", "anomaly_score", "is_anomaly"]])

    # Optional: save model
    save_path = os.path.join("data", "models", "anomaly_model.pkl")
    print(f"\nSaving model to: {save_path}")
    save_model(model, save_path)
