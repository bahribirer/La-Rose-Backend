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
        col_zones = {} 
        
        # Scan first 10 rows for headers (accumulate zones)
        for i in range(min(len(rows), 10)):
            row = rows[i]
            row_text = " ".join([t["text"].upper() for t in row])
            
            # Heuristic: Check for Header keywords
            # We look for ANY known header to trigger a scan of the line
            if any(k in row_text for k in ["BARKOD", "URUN", "FIYAT", "ADET", "MALIYET", "KAR", "STOK"]):
                for t in row:
                    txt = t["text"].strip().upper()
                    
                    # QTY Zone
                    if txt in ["ADET", "MIKTAR", "SAT.AD", "SAT. AD", "S.ADET"]:
                        col_zones["qty"] = (t["x_min"] - 0.02, t["x_max"] + 0.02)
                    
                    # TOTAL Zone
                    if txt in ["TUTAR", "TUTARI", "TOPLAM", "GENEL TOPLAM"]:
                        col_zones["total"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)
                        
                    # PRICE Zone
                    if txt in ["FIYAT", "FİYAT", "FIYATI", "BIRIM", "BİRİM FİYAT", "B.FİYAT"]:
                         col_zones["price"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)

                    # PROFIT Zone (New!)
                    # Strict check to avoid "KARSITI" matching "KAR"
                    if txt in ["KAR", "KÂR", "KAZANÇ", "ECZ.KAR", "ECZ KAR", "ECZ. KÂR"]:
                        col_zones["profit"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)

                    # COST Zone (New!)
                    if txt in ["MALİYET", "MALIYET", "ALIŞ", "ALIS", "GELİŞ", "GELIS"]:
                        col_zones["cost"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)

                    # STOCK Zone (New!)
                    if txt in ["STOK", "STOK MIK.", "STOK MİK.", "MEVCUT", "KALAN", "ELDEKİ"]:
                        col_zones["stock"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)
        
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
            exact_profit = None
            exact_cost = None
            exact_stock = None
            
            for t in row:
                t_center = t["x"]
                val = _parse_number(t["text"])
                if val is None: continue
                
                # Check Zones
                if "qty" in col_zones:
                    if col_zones["qty"][0] <= t_center <= col_zones["qty"][1]:
                        if isinstance(val, int) or (isinstance(val, float) and val.is_integer()):
                             exact_qty = int(val)
                
                if "total" in col_zones:
                    if col_zones["total"][0] <= t_center <= col_zones["total"][1]:
                        exact_total = val

                if "price" in col_zones:
                    if col_zones["price"][0] <= t_center <= col_zones["price"][1]:
                        exact_price = val

                if "profit" in col_zones:
                    if col_zones["profit"][0] <= t_center <= col_zones["profit"][1]:
                        exact_profit = val

                if "cost" in col_zones:
                    if col_zones["cost"][0] <= t_center <= col_zones["cost"][1]:
                        exact_cost = val
                        
                if "stock" in col_zones:
                     if col_zones["stock"][0] <= t_center <= col_zones["stock"][1]:
                        exact_stock = int(val)

            # Create DocumentLineItem
            doc_tokens = []
            
            for t in row:
                # Always keep barcodes
                if t["text"].isdigit() and len(t["text"]) == 13:
                     doc_tokens.append(DocumentToken(text=t["text"], layout=t["obj"].layout))
                     continue
                
                # Filter out numbers that are NOT in valid zones
                val = _parse_number(t["text"])
                if val is not None:
                    # Is it in ANY valid financial zone?
                    in_zone = False
                    for z_type, (z_min, z_max) in col_zones.items():
                        if z_min <= t["x"] <= z_max:
                            in_zone = True
                            break
                    
                    # If it's a number but NOT in a financial zone, ignore it as token
                    # (unless we want to keep it as text alias)
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
            item.exact_profit_match = exact_profit
            item.exact_cost_match = exact_cost
            item.exact_stock_match = exact_stock
            
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
