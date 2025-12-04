import io
from typing import List, Dict

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


REQUIRED_COLUMNS = ["date", "description", "amount", "category"]


def _load_csv_from_bytes(file_bytes: bytes) -> pd.DataFrame:
    """
    Read CSV from uploaded file bytes and ensure required columns exist.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))

    # Normalize column names (lowercase, strip spaces)
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Got: {list(df.columns)}")

    # Keep only the required columns for the response
    df = df[REQUIRED_COLUMNS].copy()

    # Ensure amount is numeric
    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
    )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    if df["amount"].isna().all():
        raise ValueError("Could not parse any numeric values in 'amount' column.")

    df = df.dropna(subset=["amount"])

    return df


def analyze_transactions_from_bytes(
    file_bytes: bytes,
    contamination: float = 0.05,
    top_n: int = 20,
) -> Dict:
    """
    Core anomaly detection logic for uploaded CSV bytes.
    """
    df = _load_csv_from_bytes(file_bytes)

    # we use amount as our numeric feature
    X = df[["amount"]].values

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )
    model.fit(X)

    scores = -model.decision_function(X)  # higher = more anomalous
    df["anomaly_score"] = scores

    # Sort by anomaly score descending
    df_sorted = df.sort_values("anomaly_score", ascending=False).reset_index(drop=True)

    top_n = min(top_n, len(df_sorted))
    anomalies = df_sorted.head(top_n)

    records: List[Dict] = anomalies.to_dict(orient="records")

    return {
        "total_transactions": int(len(df_sorted)),
        "returned_transactions": int(top_n),
        "anomalies": records,
    }
