import uuid
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime

from app.products.service import load_products
from app.scan.engine import run_engine
from app.scan.ocr.document_ai_client import process_document
from app.core.database import db

SCAN_DIR = Path("uploads/scans")
SCAN_DIR.mkdir(parents=True, exist_ok=True)

PRODUCT_CACHE: Optional[List[Dict]] = None


# -------------------------------------------------
# PRODUCT CACHE
# -------------------------------------------------
async def get_products_cached():
    global PRODUCT_CACHE
    if PRODUCT_CACHE is None:
        PRODUCT_CACHE = await load_products()
    return PRODUCT_CACHE


# -------------------------------------------------
# MAIN SCAN SERVICE
# -------------------------------------------------
async def scan_report_bytes(binary: bytes) -> dict:
    """
    OCR SCAN ENTRYPOINT
    - fiyatlar burada KAYBOLMAZ
    - admin panel buradan beslenir
    """

    if len(binary) > 15 * 1024 * 1024:
        raise ValueError("File too large")

    # ---------- FILE TYPE ----------
    ext = ".jpg"
    if binary[:4] == b"%PDF":
        ext = ".pdf"

    filename = f"{uuid.uuid4()}{ext}"
    path = SCAN_DIR / filename

    with open(path, "wb") as f:
        f.write(binary)

    # ---------- PRODUCTS ----------
    products = await get_products_cached()
    product_map = {p["id"]: p for p in products}

    # ---------- OCR ----------
    document = await asyncio.to_thread(
        process_document,
        str(path)
    )
    object.__setattr__(document, "file_path", str(path))

    # ---------- ENGINE ----------
    result = run_engine(
        document=document,
        product_map=product_map,
    )

    items = result.get("items", [])

    # ---------- 🔥 SAVE RAW OCR RESULT ----------
    print("\n🔍 DEBUG: PRE-SAVE SCAN ITEMS CHECK:")
    for x in items:
        print(f"   💊 Item {x.urun_id}: birim_fiyat={x.birim_fiyat} (alias unitPrice={getattr(x, 'unitPrice', 'N/A')})")

    scan_doc = {
        "createdAt": datetime.utcnow(),
        "source": "ocr",
        "file_path": str(path),
        "item_count": len(items),
        "items": [
            {
                "urun_id": i.urun_id,
                "urun_name": i.urun_name,
                "miktar": i.miktar,

                # 🔥 DEBUG LOG
                # (We use a list comprehension side-effect or just trust the logic, but let's print)
                # print(f"DEBUG SCAN SAVE: {i.urun_id} -> {i.birim_fiyat}") or similar 
                # actually print outside
            
                # 🔥 ADMIN-ONLY
                "birim_fiyat": i.birim_fiyat,
                "tutar": i.tutar,
                "maliyet": i.maliyet,
                "ecz_kar": i.ecz_kar,

                "confidence": i.match_confidence,
            }
            for i in items
        ],
    }

    insert_result = await db.scan_raw_reports.insert_one(scan_doc)

    # ---------- RESPONSE ----------
    # ---------- RESPONSE (MOBILE SAFE) ----------
    return {
        "scan_id": str(insert_result.inserted_id),
        "items": [
            {
                "urun_id": i.urun_id,
                "urun_name": i.urun_name,
                "miktar": i.miktar,
                "match_confidence": i.match_confidence,

                # 🔥 FIXED: Send financial data to mobile so it sends it back on save
                # Use camelCase for Frontend/Mobile compatibility
                "profit": i.ecz_kar,
                "cost": i.maliyet,
                "unitPrice": i.birim_fiyat,
                "totalPrice": i.tutar,
                
                # Keep snake_case for backward compatibility
                "ecz_kar": i.ecz_kar,
                "maliyet": i.maliyet,
                "birim_fiyat": i.birim_fiyat,
                "tutar": i.tutar,
            }
            for i in items
        ],
    }

