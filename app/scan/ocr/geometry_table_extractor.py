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

        # 2️⃣ Group by Rows (Barcode-Anchored Clustering)
        # Strategy: Find all barcodes first. They are the "Anchors" of each row.
        # Then assign every other token to the closest Barcode Row (vertically).
        
        barcodes = []
        others = []
        
        for t in all_tokens:
            txt = t["text"]
            # Strict Barcode Detection: 13 digits
            if txt.isdigit() and len(txt) == 13:
                barcodes.append(t)
            else:
                others.append(t)

        rows = []
        
        if not barcodes:
            print("⚠️ NO BARCODES FOUND IN GEOMETRY MODE. FALLING BACK TO BLIND LINE CLUSTERING.")
            all_tokens.sort(key=lambda k: k["y"])
            if all_tokens:
                 current_row = [all_tokens[0]]
                 for t in all_tokens[1:]:
                     if (t["y"] - current_row[0]["y"]) < 0.015: 
                         current_row.append(t)
                     else:
                         rows.append(current_row)
                         current_row = [t]
                 rows.append(current_row)
        if not barcodes:
            print("⚠️ NO BARCODES FOUND IN GEOMETRY MODE. FALLING BACK TO BLIND LINE CLUSTERING.")
            all_tokens.sort(key=lambda k: k["y"])
            if all_tokens:
                 current_row = [all_tokens[0]]
                 for t in all_tokens[1:]:
                     if (t["y"] - current_row[0]["y"]) < 0.015: 
                         current_row.append(t)
                     else:
                         rows.append(current_row)
                         current_row = [t]
                 rows.append(current_row)
        else:
            # 🏗️ COLUMN-WISE RANK MATCHING (The "Zipper" Method)
            # Curved paper destroys Global Y alignment.
            # But Vertical Order within a column is preserved.
            # 1. Detect Headers to find Column X-Bands
            # 2. Sort tokens in each band by Y
            # 3. Zip with Barcodes (Sorted by Y)
            
            barcodes.sort(key=lambda k: k["y"])
            # Initialize rows with barcodes
            # Structure: [ {barcode_token, 'extracted': {}} ]
            robust_rows = [{"barcode": b, "tokens": [b], "data": {}} for b in barcodes]
            
            # 1. DETECT HEADERS & COLUMNS
            header_tokens = []
            for t in all_tokens:
                 txt = t["text"].strip().upper()
                 h_type = None
                 if txt in ["ADET", "MIKTAR", "SAT.AD", "SAT. AD", "S.ADET", "SATILAN"]: h_type = "qty"
                 elif txt in ["TUTAR", "TUTARI", "TOPLAM", "GENEL TOPLAM", "SATIS TUTARI"]: h_type = "total"
                 elif txt in ["FIYAT", "FİYAT", "FIYATI", "BIRIM", "BİRİM FİYAT", "B.FİYAT", "S.FIYAT", "S.FİYAT", "SATIS F.", "SATIŞ F.", "PER. SAT.", "P.SATIS", "ETIKET", "ETİKET"]: h_type = "price"
                 elif txt in ["KAR", "KÂR", "KAZANÇ", "ECZ.KAR", "ECZ KAR", "ECZ. KÂR"]: h_type = "profit"
                 elif txt in ["MALİYET", "MALIYET", "ALIŞ", "ALIS", "GELİŞ", "GELIS"]: h_type = "cost"
                 elif txt in ["STOK", "STOK MIK.", "STOK MİK.", "MEVCUT", "KALAN", "ELDEKİ"]: h_type = "stock"
                 
                 if h_type:
                    header_tokens.append({"type": h_type, "x": t["x"], "x_min": t["x_min"], "x_max": t["x_max"]})
            
            col_zones = {}
            if header_tokens:
                header_tokens.sort(key=lambda k: k["x"])
                
                # INFERENCE: If Price missing but Stock/Profit exists, inject Price
                types = {h["type"] for h in header_tokens}
                if "price" not in types and "stock" in types:
                     # Find stock index
                     idx = next(i for i, h in enumerate(header_tokens) if h["type"] == "stock")
                     # Inject virtual price left of stock
                     avg_w = (header_tokens[0]["x_max"] - header_tokens[0]["x_min"])
                     virtual = {"type": "price", "x": header_tokens[idx]["x"] - 0.1, "x_min": header_tokens[idx]["x_min"] - 0.1, "x_max": header_tokens[idx]["x_min"] - 0.02}
                     header_tokens.insert(idx, virtual)

                for i, h in enumerate(header_tokens):
                    # Define Band Widths (Midpoint to Midpoint)
                    if i == 0: start = max(0.25, h["x_min"] - 0.15) # Start after barcode area
                    else: start = (header_tokens[i-1]["x_max"] + h["x_min"]) / 2
                    
                    if i == len(header_tokens) - 1: end = 1.0
                    else: end = (h["x_max"] + header_tokens[i+1]["x_min"]) / 2
                    
                    col_zones[h["type"]] = (start, end)
            else:
                 # Fallback: Default Percentages if no headers found
                 print("⚠️ NO HEADERS FOUND. USING DEFAULT ZONES.")
                 col_zones = {
                     "qty": (0.45, 0.50),
                     "price": (0.50, 0.58),
                     "total": (0.58, 0.65),
                     "stock": (0.65, 0.70),
                     "profit": (0.70, 0.80),
                     "cost": (0.80, 1.0)
                 }

            print("📐 COLUMN BANDS (ZIPPER MODE):", col_zones)

            # 2. BUCKET & SORT
            # For each column type, find ALL tokens in that X-band
            for col_type, (x_start, x_end) in col_zones.items():
                col_tokens = []
                for t in others:
                    # Filter logic: Numeric only usually? Or allow text for Qty?
                    # Let's take strict Numerics for Money columns
                    val = _parse_number(t["text"])
                    if val is not None:
                         # Exclude barcode-like numbers > 100000
                         if val > 1000000: continue 

                         if x_start <= t["x"] <= x_end:
                             col_tokens.append({"t": t, "val": val})
                
                # Sort this column's tokens by Y (Top to Bottom)
                col_tokens.sort(key=lambda k: k["t"]["y"])
                
                # 3. ZIP INTO ROWS
                # Match 1-to-1 with Barcodes
                # If counts match perfectly, it's a guaranteed match
                # If not, use Nearest Rank?
                
                print(f"   📌 Column {col_type}: Found {len(col_tokens)} items vs {len(barcodes)} rows.")
                
                # Simple Zip if counts are close or equal
                # If we have EQUAL or FEWER tokens than rows, we map i-th token to i-th row?
                # No, what if Row 1 is missing a value? Row 2's value will map to Row 1.
                # Use Y-Alignment Check to be safe.
                
                # Map each token to the row at the same "Relative Height Ranking"
                # Actually, simply checking "Is this token roughly at the same Y as the Barcode?" is safer than pure Zip if gaps exist.
                # But we are doing this because Y is unreliable globally.
                # OK, let's allow a larger Y-tolerance for "Same Row" check.
                
                col_idx = 0
                for i, row_data in enumerate(robust_rows):
                    b = row_data["barcode"]
                    
                    # Try to find a token in col_tokens that matches this barcode's Y roughly
                    # But prioritize ORDER.
                    
                    if col_idx < len(col_tokens):
                        cand = col_tokens[col_idx]
                        
                        # Validate Y-Alignment loosely
                        # Curve is usually monotonic.
                        # Difference shouldn't be massive (e.g. > 10% height)
                        if abs(cand["t"]["y"] - b["y"]) < 0.10: # 10% tolerance!
                            row_data["data"][col_type] = cand["val"]
                            row_data["tokens"].append(cand["t"])
                            col_idx += 1
                        else:
                            # Token seems too far. Maybe this row has no value for this column.
                            # Or maybe the token belongs to a later row.
                            # If token is HIGHER (smaller Y) than barcode?
                            if cand["t"]["y"] < b["y"] - 0.10:
                                # Token is way above. Skip it (belongs to header?)
                                col_idx += 1
                                # Retry check with next token?
                                if col_idx < len(col_tokens):
                                    cand = col_tokens[col_idx]
                                    if abs(cand["t"]["y"] - b["y"]) < 0.10:
                                        row_data["data"][col_type] = cand["val"]
                                        row_data["tokens"].append(cand["t"])
                                        col_idx += 1
                                pass

            # Reconstruct 'rows' list
            rows = []
            for r in robust_rows:
                # We attach the 'data' dict to the first token (barcode) for fallback extraction to find
                # Actually, the Next Step (Heuristic) will try to re-parse.
                # We should disable the Heuristic if we used Zipper?
                # Or just put tokens in 'row' and let Heuristic run?
                # Heuristic uses 'unused_numbers'. 
                # Let's attach our found values to the row tokens so the next step can find them?
                # Better: Let's just output the rows populated with tokens.
                # Our Heuristic step (Step 4) ignores zones and recalculates.
                # That will UNDO our work if we are not careful.
                # We need to explicitly modify the Heuristic Step to respect our `data` result.
                # Or just construct the row such that the Heuristic naturally works?
                # No, Heuristic is blind.
                
                # Let's inject a special attribute into the row tokens? No.
                # Let's Skip Step 4? 
                
                rows.append(r["tokens"])
                
                # CRITICAL: We need to pass the `r["data"]` to the final object construction.
                # Since `rows` is just a list of tokens...
                # We will hack it: Attach `_extracted_data` to the barcode token object.
                r["barcode"]["_extracted_data"] = r["data"]

            print(f"🧩 ZIPPER MODE: Created {len(rows)} rows with pre-mapped column data.")

        # 3️⃣ SKIP HEADERS 
        # (Already used them in Zipper)

        # 4️⃣ BYPASS HEURISTIC & USE ZIPPED DATA
        # We need to modify the loop below to check for `_extracted_data`




        # 4️⃣ Extract Data from Rows using Column Zones (STRICT MODE + WIDEST SCOPE FALLBACK)
        for row in rows:
            raw_text = " ".join([t["text"] for t in row])
            row_upper = raw_text.upper()

            # 🛑 NOISE FILTER
            if "SAYFA" in row_upper or "LISTELENEN" in row_upper or "TOPLAM" in row_upper:
                continue

            # 🔍 BARCODE CHECK
            barcodes = [t for t in row if t["text"].isdigit() and len(t["text"]) == 13]
            if not barcodes:
                continue

            exact_qty = None
            exact_total = None
            exact_price = None
            exact_profit = None
            exact_cost = None
            exact_stock = None
            
            unused_numbers = []

            for t in row:
                t_center = t["x"]
                val = _parse_number(t["text"])
                if val is None: continue
                # Skip the barcode itself from being a price/qty
                if t["text"].isdigit() and len(t["text"]) == 13 and val > 10000:
                    continue

                matched_zone = False
                
                # Check Zones First
                if "qty" in col_zones:
                    if col_zones["qty"][0] <= t_center <= col_zones["qty"][1]:
                        if (isinstance(val, int) or (isinstance(val, float) and val.is_integer())) and exact_qty is None:
                             # STRICT CAP: Qty > 50 is likely noise or code
                             if val < 50:
                                exact_qty = int(val)
                                matched_zone = True
                
                if "total" in col_zones:
                    if col_zones["total"][0] <= t_center <= col_zones["total"][1]:
                        if exact_total is None:
                            exact_total = val
                            matched_zone = True

                if "price" in col_zones:
                    if col_zones["price"][0] <= t_center <= col_zones["price"][1]:
                        if exact_price is None:
                            exact_price = val
                            matched_zone = True

                if "profit" in col_zones:
                    if col_zones["profit"][0] <= t_center <= col_zones["profit"][1]:
                        if exact_profit is None:
                            exact_profit = val
                            matched_zone = True

                if "cost" in col_zones:
                    if col_zones["cost"][0] <= t_center <= col_zones["cost"][1]:
                        if exact_cost is None:
                            exact_cost = val
                            matched_zone = True
                        
                if "stock" in col_zones:
                     if col_zones["stock"][0] <= t_center <= col_zones["stock"][1]:
                        if exact_stock is None:
                            exact_stock = int(val)
                            matched_zone = True
                
                if not matched_zone:
                    unused_numbers.append(val)
            
            # 5️⃣ SMART MAP LOGIC (Fallback or Enhancement)
            # If explicit zones failed or we want to double check against "all numbers found"
            
            # First, filter potential QTY from unused numbers if not already found
            if exact_qty is None:
                for n in unused_numbers:
                     if (isinstance(n, int) or n.is_integer()) and n < 50:
                         exact_qty = int(n)
                         unused_numbers.remove(n)
                         break
            
            # Use default Qty=1 if still missing (safe assumption for single line items usually)
            current_qty = exact_qty if exact_qty else 1

            # Now look at remaining floats to determine Cost, Price, Total
            # We have loose numbers in `unused_numbers` + any we might have assigned to `exact_...` 
            # actually let's re-evaluate everything from the pool of numbers in the row vs the slots
            
            # Collective Pool of monetary candidates (excluding the Qty we just found)
            # We want to fill: Cost, Unit Price, Total Price
            
            pool = [n for n in unused_numbers]
            # Add back verified values to pool to re-verify relative logic? 
            # No, keep zone matches if they exist. Only fill gaps from pool.
            
            pool.sort() # Smallest to Largest

            if pool:
                # Scenario A: We have 3 numbers -> Likely [Cost, UnitPrice, TotalPrice] (or [Cost, Total, Unit]?? No usually Total is largest)
                # But sometimes Cost > UnitPrice (loss).
                # MATH CHECK: P * Q = T
                
                # Try to find a pair (P, T) such that P * current_qty ~= T
                found_math_match = False
                if len(pool) >= 2 and current_qty > 1:
                     # Check all pairs
                     import itertools
                     for p, t in itertools.permutations(pool, 2):
                         if abs(p * current_qty - t) < 0.1:
                             # MSTCH!
                             if exact_price is None: exact_price = p
                             if exact_total is None: exact_total = t
                             pool.remove(p)
                             pool.remove(t)
                             found_math_match = True
                             break
                
                # If no math match (or Qty=1 where P=T), assign by size
                if not found_math_match:
                    # If we have 3 numbers, and strict zones failed:
                    # Smallest is likely Cost. Middle is Unit. Largest is Total.
                    if len(pool) == 3:
                        if exact_cost is None: exact_cost = pool[0]
                        if exact_price is None: exact_price = pool[1]
                        if exact_total is None: exact_total = pool[2]
                    
                    elif len(pool) == 2:
                        # [Small, Large] -> Likely [Unit, Total] or [Cost, Unit]
                        # If we already have Price, then [Cost, Total]?
                        # Heuristic: Users care about Unit Price and Cost.
                        if exact_price is None: exact_price = pool[0] # Assume smaller is unit price
                        if exact_total is None: exact_total = pool[1] # Assume larger is total
                        
                    elif len(pool) == 1:
                        # Just one number. Is it Unit Price or Total?
                        # If Qty=1, it's both.
                        val = pool[0]
                        if exact_price is None: exact_price = val
                        if exact_total is None: exact_total = val * current_qty

            # Final Sanity Check for relationships
            if exact_price and exact_qty and not exact_total:
                exact_total = exact_price * exact_qty
                
            # If we have a Total but no Price, infer Price
            if exact_total and exact_qty and not exact_price:
                exact_price = exact_total / exact_qty

            # If we identified a Cost, ensure it's logged
            # (Cost is often "Maliyet" or "Alış")


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
                    # This prevents "400 ML" -> "400" getting picked up as Quantity
                    if not in_zone:
                        continue 

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
