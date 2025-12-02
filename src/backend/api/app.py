"""
app.py
------
FastAPI backend for FinGuard AI.

Exposes endpoints for:
- health check
- receipt OCR and parsing
- transaction anomaly detection
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.ocr.receipt_parser import parse_receipt_from_bytes

import io
import pandas as pd

from backend.ml.anomaly_detector import (
    train_anomaly_model,
    score_transactions,
)


app = FastAPI(
    title="FinGuard AI API",
    description="Backend service for OCR-based expense auditing and anomaly detection.",
    version="0.1.0",
)

# ---------------------------------------------------------
# CORS (allow frontend / local testing)
# ---------------------------------------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "*",  # you can tighten this later
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# Basic routes
# ---------------------------------------------------------
@app.get("/")
async def root():
    return {"message": "FinGuard AI API is running"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# ---------------------------------------------------------
# Receipt OCR endpoint
# ---------------------------------------------------------
@app.post("/api/parse-receipt")
async def parse_receipt(file: UploadFile = File(...)):
    """
    Accepts an uploaded image (JPEG/PNG) and returns structured receipt data.
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/jpg"]:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Please upload a JPG or PNG image.",
        )

    image_bytes = await file.read()

    try:
        parsed = parse_receipt_from_bytes(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing receipt: {str(e)}",
        )

    return {
        "filename": file.filename,
        "parsed_receipt": parsed,
    }


# ---------------------------------------------------------
# Transaction anomaly detection endpoint
# ---------------------------------------------------------
@app.post("/api/analyze-transactions")
async def analyze_transactions(
    file: UploadFile = File(...),
    contamination: float = 0.05,
    top_n: int = 20,
):
    """
    Upload a CSV of transactions, train an unsupervised anomaly model,
    and return the most suspicious transactions.

    Expected CSV columns (at minimum):
        - date        (YYYY-MM-DD or similar)
        - merchant    (string)
        - category    (string)
        - amount      (float)

    Optional columns like transaction_id, currency, payment_method are preserved
    and returned in the output.
    """
    if file.content_type not in ["text/csv", "application/vnd.ms-excel", "application/octet-stream"]:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported file type: {file.content_type}. "
                "Please upload a CSV file."
            ),
        )

    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode("utf-8")))
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read CSV: {str(e)}",
        )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Uploaded CSV is empty.",
        )

    try:
        # Train an anomaly model on this dataset
        model = train_anomaly_model(df, contamination=contamination)

        # Score all transactions
        scored = score_transactions(model, df)

        # Sort by anomaly_score (highest = most suspicious)
        scored_sorted = scored.sort_values("anomaly_score", ascending=False)

        if top_n > 0:
            scored_top = scored_sorted.head(top_n)
        else:
            scored_top = scored_sorted

        # Convert to list of dicts for JSON response
        anomalies = scored_top.to_dict(orient="records")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing transactions: {str(e)}",
        )

    return {
        "filename": file.filename,
        "total_transactions": int(len(df)),
        "returned_transactions": int(len(anomalies)),
        "contamination": contamination,
        "anomalies": anomalies,
    }
