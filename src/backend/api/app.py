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


# ========= RECEIPT OCR ENDPOINT (STUB) =========
@app.post("/api/parse-receipt")
async def parse_receipt(file: UploadFile = File(...)):
    """
    Endpoint used by the FinGuard frontend "Receipt OCR & Parsing" section.
    Stub: returns fixed sample data so the UI matches the provided sample receipt.
    """
    if not file.filename.lower().endswith((".png", ".jpg", ".jpeg", ".pdf")):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Return stubbed sample data matching the provided example
    return {
        "filename": file.filename,
        "parsed_receipt": {
            "merchant": "Mama Lucy Shop",
            "date": "2025-12-04",
            "total_amount": 1621.68,
            "currency": "KES",
            "raw_text": (
                "Mama Lucy Shop\n"
                "Nairobi, Kenya\n\n"
                "Date: 04/12/2025 20:26\n\n"
                "Items Purchased\n"
                "----------------\n"
                "Chicken 1kg          480.00\n"
                "Rice 2kg             220.00\n"
                "Sugar 1kg            150.00\n"
                "Cooking Oil 1L       365.00\n"
                "Tomatoes              40.00\n"
                "Bread Brown           78.00\n"
                "Milk 500ml            65.00\n"
                "----------------\n"
                "Subtotal            1398.00\n"
                "VAT (16%)           223.68\n"
                "----------------\n"
                "TOTAL               1621.68 KES\n\n"
                "Payment: M-PESA\n"
                "Thank you for shopping!"
            ),
        },
    }

