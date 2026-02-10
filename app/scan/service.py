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

from app.scan.excel_parser import parse_excel_sales
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
    
    # 🧠 Hybrid Key Map: Support both ID and Barcode lookup
    product_map = {}
    for p in products:
        product_map[p["id"]] = p
        
        # Normalize barcode key for robust lookup (digits only)
        raw_bc = p.get("barcode")
        if raw_bc:
            norm_bc = "".join(c for c in str(raw_bc) if c.isdigit())
            if norm_bc:
                product_map[norm_bc] = p
    
    print(f"📦 PRODUCT MAP LOADED: {len(product_map)} keys (from {len(products)} products)")

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

                # 🔥 ADMIN-ONLY
                "birim_fiyat": i.birim_fiyat,
                "tutar": i.tutar,
                "maliyet": i.maliyet,
                "ecz_kar": i.ecz_kar,

                "confidence": i.match_confidence,
                "date": i.date,
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
                "urun_name": product_map.get(i.urun_id, {}).get("tr_name") or i.urun_name,
                "miktar": i.miktar,
                "match_confidence": i.match_confidence,

                # 🔥 FIXED: Send financial data to mobile so it sends it back on save
                # Use camelCase for Frontend/Mobile compatibility
                "profit": i.ecz_kar,
                "cost": i.maliyet,
                "unitPrice": i.birim_fiyat,
                "totalPrice": i.tutar,
                
                # Extended Financials
                "discountAmount": i.discount,
                "discount_vat": i.discount, # ✅ MATCH EXCEL UPLOAD KEY
                "taxAmount": i.tax,
                "grossTotal": i.gross_total,
                
                # Keep snake_case for backward compatibility
                "ecz_kar": i.ecz_kar,
                "maliyet": i.maliyet,
                "birim_fiyat": i.birim_fiyat,
                "tutar": i.tutar,
                "iskonto": i.discount,
                "kdv": i.tax,
                "satis_tutari": i.gross_total,
                "date": i.date,
            }
            for i in items
        ],
    }


# -------------------------------------------------
# EXCEL SCAN SERVICE
# -------------------------------------------------
async def scan_report_excel(binary: bytes) -> dict:
    """
    EXCEL SCAN ENTRYPOINT
    """
    if len(binary) > 15 * 1024 * 1024:
        raise ValueError("File too large")

    filename = f"{uuid.uuid4()}.xlsx"
    path = SCAN_DIR / filename
    
    with open(path, "wb") as f:
        f.write(binary)
        
    # ---------- PRODUCTS ----------
    products = await get_products_cached()
    product_map = {p.get("barcode"): p for p in products if p.get("barcode")}

    # ---------- PARSE ----------
    # Parse items from Excel
    parsed_items = parse_excel_sales(binary)
    
    # ---------- ENRICH & CALCULATE ----------
    items = []
    
    for pi in parsed_items:
        barcode = pi["barcode"]
        
        # Find product metadata if available
        product = product_map.get(barcode)
        
        # Use parsed data, fallback to product data, fallback to defaults
        # 1. Product Name: Excel > DB > Unknown
        urun_name = pi["urun_name"]
        if urun_name == "Bilinmeyen Ürün" and product:
            urun_name = product.get("name")
            
        # 2. Cost (Maliyet): DB > 0 (Calculated from profit if needed, but usually DB)
        maliyet = 0.0
        if product:
            try:
                maliyet = float(product.get("cost") or 0.0)
            except:
                maliyet = 0.0
            
        # 3. Unit Price (Birim Fiyat): Excel > DB > 0
        birim_fiyat = pi["birim_fiyat"]
        if birim_fiyat <= 0 and product:
             try:
                birim_fiyat = float(product.get("price") or 0.0)
             except:
                birim_fiyat = 0.0
             
        # 4. Tutar (Net Sales): Excel > Calculated
        tutar = pi["tutar"]
        # If Excel parser calculated it as (price*qty - discount), use it.
        # If it was 0 (missing price), recalc if we found price in DB
        if tutar <= 0 and birim_fiyat > 0:
            quantity = pi["miktar"]
            discount = pi["discount_vat"]
            tutar = (birim_fiyat * quantity) - discount
            if tutar < 0: tutar = 0
            
        # 5. Profit (Kar): Net Sales - (Cost * Qty)
        # Net Sales (Tutar) is tax-exclusive revenue ideally.
        # If 'maliyet' is per unit cost.
        total_cost = maliyet * pi["miktar"]
        ecz_kar = tutar - total_cost
        
        items.append({
            "urun_id": str(product["_id"]) if product else None, # Real ID if found
            "barcode": barcode,
            "urun_name": urun_name,
            "miktar": pi["miktar"],
            "birim_fiyat": birim_fiyat,
            "tutar": tutar, # Net Sales
            "maliyet": maliyet, # Unit cost
            "ecz_kar": ecz_kar, # Total profit
            "discount_vat": pi["discount_vat"],
            "stock": pi.get("stock", 0),
            "discount_vat": pi["discount_vat"],
            "discount_vat": pi["discount_vat"],
            "match_confidence": 1.0 if product else 0.5, # Excel is definite, effectively
            "original_row": pi["raw_row"],
            "date": pi.get("date")
        })
        
    # ---------- SAVE RAW REPORT ----------
    scan_doc = {
        "createdAt": datetime.utcnow(),
        "source": "excel",
        "file_path": str(path),
        "item_count": len(items),
        "items": items
    }
    
    insert_result = await db.scan_raw_reports.insert_one(scan_doc)
    
    # ---------- RESPONSE ----------
    return {
        "scan_id": str(insert_result.inserted_id),
        "items": [
            {
                "urun_id": i["urun_id"] or i["barcode"],
                "urun_name": i["urun_name"],
                "miktar": i["miktar"],
                "match_confidence": i["match_confidence"],
                
                # Mobile/Frontend keys
                "profit": i["ecz_kar"],
                "cost": i["maliyet"],
                "unitPrice": i["birim_fiyat"],
                "totalPrice": i["tutar"],
                "barcode": i["barcode"],
                "stock": i["stock"],
                
                # Extended Financials
                "discountAmount": i["discount_vat"],
                "taxAmount": 0.0,
                "grossTotal": i["tutar"] + i["discount_vat"],
                
                # Legacy
                "ecz_kar": i["ecz_kar"],
                "maliyet": i["maliyet"],
                "birim_fiyat": i["birim_fiyat"],
                "tutar": i["tutar"],
                "iskonto": i["discount_vat"],
                "satis_tutari": i["tutar"] + i["discount_vat"],
                "date": i.get("date"), # ✅ FIX: Passthrough date to mobile
            }
            for i in items
        ]
    }

