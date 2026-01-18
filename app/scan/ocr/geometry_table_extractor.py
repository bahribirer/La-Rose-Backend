from typing import List, Dict, Optional, Tuple
from collections import defaultdict
import re

from app.scan.models.document_line_item import DocumentLineItem, DocumentToken

def extract_items_by_geometry(document) -> List[DocumentLineItem]:
    """
    Manually reconstructs table rows based on Y-coordinates of text blocks.
    Then uses X-coordinates to map values to columns (Qty, Price, Total).
    Bypasses Document AI's 'Table' detection.
    """
    items: List[DocumentLineItem] = []
    
    for page in document.pages:
        # 1️⃣ Collect all tokens with their geometry
        all_tokens = []
        source_items = getattr(page, "tokens", [])
        
        for token in source_items:
            text = _get_text(document, token.layout.text_anchor)
            if not text.strip():
                continue
                
            # Get center coordinates
            vertices = token.layout.bounding_poly.normalized_vertices
            if not vertices:
                continue
                
            y_center = sum(v.y for v in vertices) / len(vertices)
            x_center = sum(v.x for v in vertices) / len(vertices)
            x_min = min(v.x for v in vertices)
            x_max = max(v.x for v in vertices)
            
            all_tokens.append({
                "text": text,
                "y": y_center,
                "x": x_center,
                "x_min": x_min,
                "x_max": x_max,
                "obj": token
            })

        # 2️⃣ Group by Rows (Cluster Y coordinates)
        # Sort by Y
        all_tokens.sort(key=lambda k: k["y"])
        
        # Stricter tolerance to prevent merging lines
        Y_TOLERANCE = 0.010
        
        rows = []
        current_row = []
        if all_tokens:
            current_y = all_tokens[0]["y"]
            
            for t in all_tokens:
                if abs(t["y"] - current_y) < Y_TOLERANCE: 
                    current_row.append(t)
                else:
                    # New row
                    _finalize_row(rows, current_row)
                    current_row = [t]
                    current_y = t["y"]
            
            if current_row:
                _finalize_row(rows, current_row)

        # 3️⃣ Detect Headers & Define Column Zones (X-Ranges)
        col_zones = {} # "qty": (x_min, x_max), "total": ...
        
        # Scan first 10 rows for headers (accumulate zones)
        for i in range(min(len(rows), 10)):
            row = rows[i]
            row_text = " ".join([t["text"].upper() for t in row])
            
            # Heuristic: Check for Header keywords
            if "BARKOD" in row_text or "URUN ADI" in row_text or "FIYAT" in row_text or "ADET" in row_text:
                for t in row:
                    txt = t["text"].upper()
                    if "ADET" in txt or "MIKTAR" in txt or "SAT.AD" in txt:
                        if "STOK" not in txt:
                             col_zones["qty"] = (t["x_min"] - 0.02, t["x_max"] + 0.02)
                    
                    if "TUTAR" in txt or "TOPLAM" in txt:
                        col_zones["total"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)
                        
                    if "FIYAT" in txt or "BIRIM" in txt:
                         col_zones["price"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)
        
        if col_zones:
             print("📐 GEOMETRIC HEADERS FOUND:", col_zones)

        # 4️⃣ Extract Data from Rows using Column Zones (STRICT MODE)
        for row in rows:
            raw_text = " ".join([t["text"] for t in row])
            row_upper = raw_text.upper()

            # 🛑 NOISE FILTER: Skip Page No, List Count, Summary Lines
            if "SAYFA" in row_upper or "LISTELENEN" in row_upper or "TOPLAM" in row_upper:
                continue

            # 🔍 BARCODE CHECK: Strict "Product Row" definition
            # A valid product row MUST have a 13-digit barcode (or at least look like one)
            barcodes = [t for t in row if t["text"].isdigit() and len(t["text"]) == 13]
            
            # If NO barcode, it's likely a header, footer, or garbage text line -> SKIP
            if not barcodes:
                continue

            # Try to extract structured values based on Zones
            exact_qty = None
            exact_total = None
            exact_price = None
            
            for t in row:
                t_center = t["x"]
                val = _parse_number(t["text"])
                if val is None: continue
                
                # Check Qty Zone
                if "qty" in col_zones:
                    z_min, z_max = col_zones["qty"]
                    if z_min <= t_center <= z_max:
                        # Ensure it's integer-ish
                        if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
                             exact_qty = int(val)
                
                # Check Total Zone
                if "total" in col_zones:
                    z_min, z_max = col_zones["total"]
                    if z_min <= t_center <= z_max:
                        exact_total = val

                # Check Price Zone
                if "price" in col_zones:
                    z_min, z_max = col_zones["price"]
                    if z_min <= t_center <= z_max:
                        exact_price = val

            # Create DocumentLineItem
            # Pass tokens so `table_line_parser` can find barcode!
            doc_tokens = []
            
            for t in row:
                # Always keep barcodes
                if t["text"].isdigit() and len(t["text"]) == 13:
                     doc_tokens.append(DocumentToken(text=t["text"], layout=t["obj"].layout))
                     continue
                
                # Filter out numbers that are NOT in valid zones to prevent "400 ML" -> Qty errors
                # If we have zones, strictly enforce them for pure numbers
                val = _parse_number(t["text"])
                if val is not None:
                    # Is it in ANY valid financial zone?
                    in_zone = False
                    if "qty" in col_zones and col_zones["qty"][0] <= t["x"] <= col_zones["qty"][1]: in_zone = True
                    elif "price" in col_zones and col_zones["price"][0] <= t["x"] <= col_zones["price"][1]: in_zone = True
                    elif "total" in col_zones and col_zones["total"][0] <= t["x"] <= col_zones["total"][1]: in_zone = True
                    
                    # If it's a number but NOT in a financial zone, treat it as text (e.g. part of Product Name)
                    # BUT `line_report_parser` often grabs the "first number" it sees.
                    # So we should probably NOT send it as a separate token if it risks confusing the parser.
                    # HOWEVER, we need the text for the description.
                    # Let's keep it, but relying on `extracted` values is safer.
                    pass 

                doc_tokens.append(DocumentToken(
                    text=t["text"],
                    layout=t["obj"].layout
                ))
            
            item = DocumentLineItem(
                raw_text=raw_text,
                tokens=doc_tokens,
                confidence=0.95, # High confidence for Geometry match
                source="GEOMETRY"
            )
            item.exact_quantity_match = exact_qty
            item.exact_total_match = exact_total
            item.exact_price_match = exact_price
            
            items.append(item)

    return items


def _finalize_row(rows, current_row):
    """
    Checks if a row contains multiple barcodes. If so, splits it.
    Otherwise appends to rows.
    """
    if not current_row:
        return

    # Sort by X to check content
    current_row.sort(key=lambda k: k["x"])
    
    # Check for multiple barcodes
    barcodes = []
    for t in current_row:
        # Simple barcode check (13 digits usually)
        if t["text"].isdigit() and len(t["text"]) == 13:
             barcodes.append(t)
    
    if len(barcodes) > 1:
        print(f"⚠️ MERGED ROW DETECTED ({len(barcodes)} barcodes). Splitting...")
        # Split logic: Assign tokens to the closest barcode's Y "plane"
        # This is a sub-clustering problem.
        # Let's verify if their Y's are actually distinct enough to split
        barcodes.sort(key=lambda k: k["y"])
        
        # Create sub-rows based on barcode Ys
        sub_rows = {id(b): [b] for b in barcodes}
        barcode_ys = {id(b): b["y"] for b in barcodes}
        
        for t in current_row:
            # Skip the barcodes themselves (already added)
            if any(t["obj"] == b["obj"] for b in barcodes):
                continue
                
            # Find closest barcode Y
            closest_bid = min(barcode_ys.keys(), key=lambda bid: abs(t["y"] - barcode_ys[bid]))
            
            sub_rows[closest_bid].append(t)
            
        # Add the split rows
        for b in barcodes:
            r = sub_rows[id(b)]
            r.sort(key=lambda k: k["x"])
            rows.append(r)
    else:
        rows.append(current_row)


def _parse_number(text: str):
    text = text.strip()
    if not text: return None
    
    try:
        # Smart detection for US vs TR format
        # Case 1: Both separators exist (e.g., 1,234.56 or 1.234,56)
        if "." in text and "," in text:
            last_dot = text.rfind(".")
            last_comma = text.rfind(",")
            if last_dot > last_comma:
                # US Format: 1,234.56 -> Remove comma, keep dot
                return float(text.replace(",", ""))
            else:
                # TR Format: 1.234,56 -> Remove dot, replace comma with dot
                return float(text.replace(".", "").replace(",", "."))
                
        # Case 2: Only Dot (e.g., 123.45 or 1.234)
        elif "." in text:
             return float(text)
            
        # Case 3: Only Comma (e.g., 123,45)
        elif "," in text:
            return float(text.replace(",", "."))
            
        return int(text)
    except:
        return None

def _get_text(document, anchor):
    text = ""
    for seg in anchor.text_segments:
        start = seg.start_index or 0
        end = seg.end_index
        text += document.text[start:end]
    return text.strip()
