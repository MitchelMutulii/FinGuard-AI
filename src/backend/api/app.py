# src/backend/api/app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.ml.anomaly_detector import analyze_transactions_from_bytes

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= CSV ANOMALY ANALYSIS =========
@app.post("/api/analyze-transactions")
async def analyze_transactions(
    file: UploadFile = File(...),
    contamination: float = Form(0.05),
    top_n: int = Form(20),
):
    try:
        contents = await file.read()
        result = analyze_transactions_from_bytes(contents, contamination, top_n)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")


# ========= RECEIPT OCR STUB ENDPOINT =========
@app.post("/api/receipt/parse")
async def parse_receipt(file: UploadFile = File(...)):
    """
    Endpoint used by the FinGuard frontend "Receipt OCR & Parsing" section.
    For now this is a stub that just returns dummy data so the UI works.
    You can plug in real Tesseract logic later.
    """
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # TODO: run real OCR here. For now, return a fake parsed receipt.
    return {
        "merchant": "Demo Supermarket",
        "date": "2025-12-04",
        "total": 1234.56,
        "currency": "KES",
        "rawText": "DUMMY RECEIPT TEXT - hook up Tesseract later",
    }

