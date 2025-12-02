"""
receipt_parser.py
-----------------
OCR + basic parsing for FinGuard AI.

Functions:
- extract_text_from_image_path(path)  -> raw text
- extract_text_from_bytes(bytes)      -> raw text
- parse_receipt_text(text)            -> structured dict
- parse_receipt_from_path(path)       -> dict
- parse_receipt_from_bytes(bytes)     -> dict
"""

import io
import re
from datetime import datetime
from typing import Optional, Dict, Any

import cv2
import numpy as np
import pytesseract
from PIL import Image


# ************************************************************
# 1. CONFIGURE TESSERACT PATH (WINDOWS)
# ************************************************************

# ⚠️ EDIT THIS PATH to match your installation if needed.
# Example default install path:
# C:\\Program Files\\Tesseract-OCR\\tesseract.exe

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ************************************************************
# 2. IMAGE PREPROCESSING
# ************************************************************

def _preprocess_image_for_ocr(image: np.ndarray) -> np.ndarray:
    """
    Basic preprocessing to improve OCR accuracy:
    - convert to grayscale
    - denoise slightly
    - adaptive thresholding (binarization)
    - optional resizing
    """
    # Convert to gray
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Denoise a bit
    gray = cv2.medianBlur(gray, 3)

    # Adaptive threshold (better for uneven lighting)
    thresh = cv2.adaptiveThreshold(
        gray,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY,
        blockSize=31,
        C=10,
    )

    # Upscale small images to help OCR
    h, w = thresh.shape
    if max(h, w) < 1000:
        scale_factor = 1000 / max(h, w)
        thresh = cv2.resize(
            thresh,
            None,
            fx=scale_factor,
            fy=scale_factor,
            interpolation=cv2.INTER_CUBIC,
        )

    return thresh


# ************************************************************
# 3. OCR UTILITIES
# ************************************************************

def extract_text_from_image_path(image_path: str) -> str:
    """
    Read an image from disk, preprocess it, and run Tesseract OCR.
    Returns the raw extracted text.
    """
    image = cv2.imread(image_path)
    if image is None:
        raise FileNotFoundError(f"Could not read image at: {image_path}")

    preprocessed = _preprocess_image_for_ocr(image)

    # Use English by default, you can add other langs if needed (e.g. "eng+fra")
    text = pytesseract.image_to_string(preprocessed, lang="eng")

    return text


def extract_text_from_bytes(image_bytes: bytes) -> str:
    """
    Accept raw image bytes (e.g. from FastAPI upload),
    convert to cv2 image, preprocess, and OCR.
    """
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    preprocessed = _preprocess_image_for_ocr(image)
    text = pytesseract.image_to_string(preprocessed, lang="eng")

    return text


# ************************************************************
# 4. RECEIPT TEXT PARSING
# ************************************************************

DATE_PATTERNS = [
    r"(\d{4}[-/]\d{2}[-/]\d{2})",        # 2025-12-02 or 2025/12/02
    r"(\d{2}[-/]\d{2}[-/]\d{4})",        # 02-12-2025 or 02/12/2025
    r"(\d{2}\s+[A-Za-z]{3,9}\s+\d{4})",  # 02 Dec 2025
]

AMOUNT_PATTERN = r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{2})?)"  # 1,234.56 or 1234.56


def _extract_date(text: str) -> Optional[str]:
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            candidate = match.group(1)
            # Try to normalize to ISO format if possible
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y", "%d %b %Y", "%d %B %Y"):
                try:
                    dt = datetime.strptime(candidate, fmt)
                    return dt.date().isoformat()
                except ValueError:
                    continue
            # If parsing fails, just return raw
            return candidate
    return None


def _extract_total_amount(text: str) -> Optional[float]:
    """
    Try to find the 'Total' amount on the receipt.
    Strategy:
      - Look for lines containing 'total'
      - On those lines, grab the last number that looks like an amount
      - Fallback: largest amount in entire text
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    amount_candidates = []

    # 1) Search lines mentioning "total"
    for line in lines:
        if "total" in line.lower():
            matches = re.findall(AMOUNT_PATTERN, line)
            if matches:
                # Last amount in the line is often the actual total
                last = matches[-1].replace(",", "").replace(" ", "")
                try:
                    return float(last)
                except ValueError:
                    pass

    # 2) Fallback: collect all amounts and pick the largest
    for line in lines:
        for match in re.findall(AMOUNT_PATTERN, line):
            clean = match.replace(",", "").replace(" ", "")
            try:
                amount_candidates.append(float(clean))
            except ValueError:
                continue

    if amount_candidates:
        return max(amount_candidates)

    return None


def _guess_merchant_name(text: str) -> Optional[str]:
    """
    Heuristic: merchant is usually in the first 1–3 non-empty lines.
    """
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None

    # Skip obvious non-merchant lines (e.g. "Receipt", "Invoice")
    for line in lines[:3]:
        if len(line) < 3:
            continue
        lower = line.lower()
        if any(keyword in lower for keyword in ["receipt", "invoice", "tax", "vat"]):
            continue
        return line

    return lines[0] if lines else None


def parse_receipt_text(text: str) -> Dict[str, Any]:
    """
    Turn raw OCR text into a structured dictionary.
    """
    merchant = _guess_merchant_name(text)
    date = _extract_date(text)
    total = _extract_total_amount(text)

    return {
        "merchant": merchant,
        "date": date,
        "total_amount": total,
        "currency": None,  # you can try to infer this later (KES, USD, etc.)
        "raw_text": text,
    }


# ************************************************************
# 5. HIGH-LEVEL HELPERS (for API use)
# ************************************************************

def parse_receipt_from_path(image_path: str) -> Dict[str, Any]:
    """
    Full pipeline: image path -> OCR -> parsed receipt.
    """
    text = extract_text_from_image_path(image_path)
    parsed = parse_receipt_text(text)
    return parsed


def parse_receipt_from_bytes(image_bytes: bytes) -> Dict[str, Any]:
    """
    Full pipeline: image bytes -> OCR -> parsed receipt.
    Ideal for FastAPI file uploads.
    """
    text = extract_text_from_bytes(image_bytes)
    parsed = parse_receipt_text(text)
    return parsed


# For quick local testing
if __name__ == "__main__":
    sample_path = "data/sample_receipts/example1.jpg"  # update to your test image
    result = parse_receipt_from_path(sample_path)
    print("Parsed receipt:")
    print(result)
