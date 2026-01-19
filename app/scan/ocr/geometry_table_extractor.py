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
        else:

            # 🏗️ SKEW CORRECTION (Holistic Rotation)
            import math
            
            # 1. Calculate Skew Angle from Headers 
            # Use headers because they span the full width and form a line
            header_tokens_raw = []
            for t in all_tokens:
                 txt = t["text"].strip().upper()
                 if txt in ["BARKOD", "URUN ADI", "ÜRÜN ADI", "MIKTAR", "ADET", "NET SATIŞ", "TUTAR", "TOPLAM"]:
                     header_tokens_raw.append(t)
            
            rotation_angle = 0.0
            if len(header_tokens_raw) > 2:
                # Simple Linear Regression: y = mx + c
                # slope m ~ tan(angle)
                avg_x = sum(t["x"] for t in header_tokens_raw) / len(header_tokens_raw)
                avg_y = sum(t["y"] for t in header_tokens_raw) / len(header_tokens_raw)
                
                numerator = sum((t["x"] - avg_x) * (t["y"] - avg_y) for t in header_tokens_raw)
                denominator = sum((t["x"] - avg_x) ** 2 for t in header_tokens_raw)
                
                if denominator != 0:
                    slope = numerator / denominator
                    rotation_angle = math.atan(slope)
                    print(f"🔄 RAW DETECTED SKEW ANGLE: {math.degrees(rotation_angle):.2f} degrees")
                    
                    # 🛡️ SAFETY CLAMP: Max 5 degrees rotation
                    # Pharmacy receipts are rarely rotated > 5deg.
                    # Large angles usually mean the regression found widely scattered headers (not a line).
                    MAX_ROTATION = math.radians(5.0)
                    if abs(rotation_angle) > MAX_ROTATION:
                        print(f"⚠️ ROTATION TOO LARGE ({math.degrees(rotation_angle):.2f} deg). CLAMPING to 0.")
                        rotation_angle = 0.0 # Better to not rotate than to destroy it
                    else:
                        print(f"✅ APPLYING SKEW CORRECTION: {math.degrees(rotation_angle):.2f} degrees")

            # 2. Rotate All Tokens
            # Center of rotation doesn't matter much for relative alignment, use (0.5, 0.5)
            cx, cy = 0.5, 0.5
            cos_a = math.cos(-rotation_angle)
            sin_a = math.sin(-rotation_angle)
            
            rotated_tokens = []
            for t in all_tokens:
                # Translate to origin
                tx = t["x"] - cx
                ty = t["y"] - cy
                
                # Rotate
                rx = tx * cos_a - ty * sin_a
                ry = tx * sin_a + ty * cos_a
                
                # Translate back
                new_x = rx + cx
                new_y = ry + cy
                
                # Clone token with new coords
                new_t = t.copy()
                new_t["x"] = new_x
                new_t["y"] = new_y
                
                # Recalculate Min/Max based on new center and original width
                # This fixes the "Inverted Zones" bug where sorted X disagreed with old X_min/max
                w = t.get("x_max", t["x"]) - t.get("x_min", t["x"])
                if w < 0: w = 0 # Safety
                
                new_t["x_min"] = new_x - (w / 2)
                new_t["x_max"] = new_x + (w / 2)
                
                rotated_tokens.append(new_t)
                
            # USE ROTATED TOKENS FOR GEOMETRY
            all_tokens = rotated_tokens
            
            # Re-identify types
            barcodes = []
            others = []
            for t in all_tokens:
                txt = t["text"]
                if txt.isdigit() and len(txt) == 13:
                    barcodes.append(t)
                else:
                    others.append(t)

            rows = []

            if not barcodes:
                print("⚠️ NO BARCODES FOUND IN GEOMETRY MODE (POST-ROTATION).")
                # (Fallback Logic omitted for brevity, usually barcodes exist)
            else:
                # 🏗️ BARCODE-CENTRIC ROW SOLVER ("Semantic Row Parser")
                # Instead of defining vertical zones (which fail on skew/shift),
                # we group ALL tokens near a barcode into a "Row Bag" and solve the math.

                barcodes.sort(key=lambda k: k["y"])
                robust_rows = [{"barcode": b, "tokens": [b], "data": {}} for b in barcodes]

                # 1. PRE-COMPUTE CANDIDATES & IDENTIFY GLOBAL NOISE
                # Strategy: "Token-to-Nearest-Barcode"
                # To handle skew/curve, we allow a wide vertical tolerance (e.g. 5-8% of page).
                # But to prevent rows stealing each other's data, each token is assigned ONLY to its closest barcode.

                from collections import defaultdict
                global_number_counts = defaultdict(int)
                
                # Prepare rows dict for quick access
                # robust_rows is a list of dicts.
                
                # Initialize candidates list for each row
                for r in robust_rows:
                    r["temp_candidates"] = []

                # Iterate ALL non-barcode tokens
                for t in others:
                    val = _parse_number(t["text"])
                    if val is None: continue
                    
                    # Count for Global Noise
                    global_number_counts[val] += 1

                    # Find Closest Barcode
                    best_row = None
                    min_dist = 0.08 # Wide tolerance (8% of page height) to catch skewed numbers
                    
                    for r in robust_rows:
                        dist = abs(t["y"] - r["barcode"]["y"])
                        if dist < min_dist:
                            min_dist = dist
                            best_row = r
                    
                    # Assign to best row
                    if best_row:
                        # Calculate X-distance for later sorting
                        x_dist = abs(t["x"] - best_row["barcode"]["x"])
                        best_row["temp_candidates"].append({"t": t, "val": val, "dist": x_dist})

                # Sort candidates in each row by X (Left-to-Right)
                for r in robust_rows:
                    r["temp_candidates"].sort(key=lambda k: k["t"]["x"])

                # Identify Blacklist (Repeating Numbers)
                # If a number appears in > 3 rows OR > 50% of rows (if rows > 2)
                # Exception: Small integers < 50 (Quantity often repeats 1, 1, 1...)
                blacklist = set()
                total_rows = len(robust_rows)
                threshold = 3 
                if total_rows > 5:
                    threshold = max(3, total_rows * 0.4)
                
                for val, count in global_number_counts.items():
                    # Allow small integers (Qty) to repeat
                    if (isinstance(val, int) or val.is_integer()) and val < 50:
                        continue
                    if count > threshold:
                        print(f"🔇 GLOBAL NOISE FILTER: Ignoring repeating value {val} (found in {count} rows)")
                        blacklist.add(val)

                # 2. RUN SEMANTIC SOLVER
                for r in robust_rows:
                    # Filter candidates
                    row_candidates = [c for c in r["temp_candidates"] if c["val"] not in blacklist]
                    
                    # We have a bag of numbers: e.g. [1, 792.0, 884.28]
                    # Goal: Assign Qty, Price, Total, Cost, Profit etc.
                    
                    nums = [c["val"] for c in row_candidates]
                    
                    qty = 1
                    financials = []

                    # A. Identify Quantity (Small Integer < 50)
                    # Heuristic: The small integer immediately to the right of barcode is likely Qty.
                    # Or just any small integer in the row.
                    potential_qtys = [n for n in nums if isinstance(n, int) and n < 50]
                    
                    if potential_qtys:
                        # Prioritize the one closest to Barcode? Or just the first one?
                        # Usually Qty is the first number after Description.
                        qty = potential_qtys[0]
                        # Remove it from financials list to avoid confusion
                        # (Remove only one instance of it)
                        nums.remove(qty)
                        r["data"]["qty"] = qty
                        
                        # Add token to row
                        for c in row_candidates:
                            if c["val"] == qty:
                                r["tokens"].append(c["t"])
                                break
                    else:
                        r["data"]["qty"] = 1 # Default

                    # B. Identify Financials
                    # Remaining numbers are likely monetary.
                    # Sort them: Profit < Cost < Price < Total (usually)
                    # But if Qty=1, Price=Total.
                    # If Net/Gross exists, Total might be larger.
                    
                    financials = sorted([n for n in nums if n >= 0.5]) # Filter tiny noise
                    
                    # Store finding
                    r["data"]["financials"] = financials
                    
                    # Logic Tree:
                    if len(financials) == 0:
                        pass # No data
                    
                    elif len(financials) == 1:
                        # Only one number? It's likely the Total Price.
                        r["data"]["total"] = financials[0]
                        r["data"]["price"] = financials[0] / qty
                        
                    elif len(financials) >= 2:
                        # [Small, Large] -> [Profit, Total]? or [Price, Cost]?
                        # Try to find Relationship: A * Qty = B
                        
                        # 1. Try Additive Relationship first (Profit + Cost = Total)
                        # This generates the most confidence because it explains 3 numbers.
                        found_additive = False
                        if len(financials) >= 3:
                            for i in range(len(financials)):
                                for j in range(len(financials)):
                                    for k in range(len(financials)):
                                        if i == j or i == k or j == k: continue
                                        A = financials[i]
                                        B = financials[j]
                                        C = financials[k] # Potential Total
                                        
                                        # Tolerance check for A + B = C
                                        if abs((A + B) - C) < 0.5:
                                            # We found Profit + Cost = Total!
                                            # Usually Cost > Profit, but not always.
                                            # C is definitely Total.
                                            r["data"]["total"] = C
                                            r["data"]["cost"] = max(A, B) # Assumption: Cost is usually larger than Profit
                                            r["data"]["profit"] = min(A, B) 
                                            
                                            found_additive = True
                                            
                                            # The remaining number is likely "List Price"
                                            remaining = [f for f in financials if f not in (A, B, C)]
                                            if remaining:
                                                r["data"]["price"] = remaining[0]
                                            else:
                                                # If no List Price found, use Total/Qty (Net Price)
                                                r["data"]["price"] = C / qty
                                            break
                                    if found_additive: break
                                if found_additive: break

                        if not found_additive:
                            # 2. Try Multiplicative Relationship (Price * Qty = Total)
                            found_relation = False
                            for i in range(len(financials)):
                                for j in range(len(financials)):
                                    if i == j: continue
                                    A = financials[i]
                                    B = financials[j]
                                    
                                    # Tolerance for float math (OCR noise)
                                    if abs((A * qty) - B) < 0.5:
                                        r["data"]["price"] = A
                                        r["data"]["total"] = B
                                        found_relation = True
                                        break
                                if found_relation: break
                            
                            if not found_relation:
                                # Fallback: Largest is Total.
                                max_val = financials[-1]
                                r["data"]["total"] = max_val
                                
                                if qty == 1:
                                    r["data"]["price"] = max_val
                                else:
                                    r["data"]["price"] = max_val / qty
                                
                                # Fallback 2: Identify Cost / Profit from remainder
                                remaining = [f for f in financials if f != r["data"].get("price") and f != r["data"].get("total")]
                                remaining = sorted(list(set(remaining)))
                                
                                if remaining:
                                    r["data"]["cost"] = remaining[-1]
                                    if len(remaining) > 1:
                                        r["data"]["profit"] = remaining[0]

                    # C. Identify Stock (Secondary Small Integer)
                    # We already picked one small int as 'qty'.
                    # Any other small int in the row could be 'stock'.
                    # Image shows 'Stock' column exists.
                    potential_stocks = [n for n in nums if isinstance(n, int) and n < 1000 and n != r["data"].get("qty")]
                    if potential_stocks:
                        # If multiple, picking one is hard.
                        # Heuristic: Stock is usually AFTER Total or BEFORE Profit.
                        # For now, just pick the first available one as best guess.
                         r["data"]["stock"] = potential_stocks[0]
                    
                    # Mark tokens as used
                    for c in row_candidates:
                        if c["val"] in financials:
                             r["tokens"].append(c["t"])
                             # extracted_data logic handles values, tokens just for viz/debug
                             pass

            rows = []
            for r in robust_rows:
                rows.append(r["tokens"])
                r["barcode"]["_extracted_data"] = r["data"]

            print(f"🧩 SEMANTIC SOLVER: Extracted {len(rows)} rows.")

        # 3️⃣ NO-OP HEADERS
        
        # 4️⃣ PARSER LOOP
        # We assume 'rows' contains lists of tokens.
        # If Zone Magnet was used, the barcode token has '_extracted_data' attached.
        
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
            exact_tax = None
            exact_net_total = None
            
            # --- ZONE MAGNET DATA INJECTION ---
            if "_extracted_data" in barcodes[0]:
                data = barcodes[0]["_extracted_data"]
                exact_qty = data.get("qty")
                exact_total = data.get("total")
                exact_price = data.get("price")
                exact_cost = data.get("cost")
                exact_profit = data.get("profit")
                exact_stock = data.get("stock")
                exact_tax = data.get("tax")
                exact_net_total = data.get("net_total")
                
                # INFERENCE: Calculate Total from Net+Tax if needed
                if exact_net_total and exact_tax and not exact_total:
                     exact_total = exact_net_total + exact_tax
                
                # INFERENCE: If we have Sales Total but no Unit Price, calc it
                if exact_total and exact_qty and not exact_price:
                     exact_price = exact_total / exact_qty

            unused_numbers = []

            for t in row:
                t_center = t["x"]
                val = _parse_number(t["text"])
                if val is None: continue
                # Skip the barcode itself and massive numbers
                if t["text"].isdigit() and len(t["text"]) == 13:
                    continue
                if val > 1000000:
                    continue

                # Collect all numbers for Heuristic Mapper (Fallback)
                # But don't duplicate if already extracted by Semantic Solver
                if val not in [exact_qty, exact_total, exact_price, exact_cost, exact_profit, exact_stock, exact_net_total]:
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
                
                # Filter out numbers that are NOT in valid zones -> REMOVED because we are using Semantic Solver now.
                # All numbers in the row are candidates.
                val = _parse_number(t["text"])
                if val is not None:
                     # (Optional: Add size checks here if needed)
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
