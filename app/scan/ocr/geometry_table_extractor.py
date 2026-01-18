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
            # Fallback to previous logic
            all_tokens.sort(key=lambda k: k["y"])
            if all_tokens:
                 current_row = [all_tokens[0]]
                 for t in all_tokens[1:]:
                     if (t["y"] - current_row[0]["y"]) < 0.01: 
                         current_row.append(t)
                     else:
                         rows.append(current_row)
                         current_row = [t]
                 rows.append(current_row)
        else:
            # We have barcodes. Create a row for each.
            barcodes.sort(key=lambda k: k["y"])
            row_map = {id(b): [b] for b in barcodes}
            
            # Calculate dynamic zones for each barcode
            # We want to claim ~45% of the space up and down, leaving 10% gaps
            row_zones = {}
            
            # Estimate average spacing for edge cases
            avg_spacing = 0.05 # Default 5%
            if len(barcodes) > 1:
                spacings = [barcodes[i+1]["y"] - barcodes[i]["y"] for i in range(len(barcodes)-1)]
                avg_spacing = sum(spacings) / len(spacings)

            for i in range(len(barcodes)):
                b = barcodes[i]
                bid = id(b)
                y = b["y"]
                
                # Distance to Previous
                if i == 0:
                    delta_prev = avg_spacing
                else:
                    delta_prev = y - barcodes[i-1]["y"]
                
                # Distance to Next
                if i == len(barcodes) - 1:
                    delta_next = avg_spacing
                else:
                    delta_next = barcodes[i+1]["y"] - y
                
                # Define Zone: center +/- 45% of spacing
                # Note: barcodes[i-1].y + 0.55*gap is the same as y - 0.45*gap roughly?
                # Let's simple use relative boundary from Center
                top_boundary = y - (delta_prev * 0.45)
                bottom_boundary = y + (delta_next * 0.45)
                
                row_zones[bid] = (top_boundary, bottom_boundary)

            # Assign other tokens to their safe zone
            for t in others:
                y = t["y"]
                assigned = False
                for bid, (top, bottom) in row_zones.items():
                    if top <= y <= bottom:
                        row_map[bid].append(t)
                        assigned = True
                        break
                
                if not assigned:
                    # Token is in the "No Man's Land" (Gap) or Header section -> Noise
                    pass

            # Convert map to list of rows
            for b in barcodes:
                r = row_map[id(b)]
                r.sort(key=lambda k: k["x"]) 
                rows.append(r)

            print(f"🧩 BARCODE SAFE SLICING: Created {len(rows)} robust rows via ADAPTIVE ZONES.")

        # 3️⃣ Detect Headers & Define DISJOINT Column Zones
        header_tokens = []
        
        # We look for header keywords in scan of all tokens
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
            # Sort headers by X position
            header_tokens.sort(key=lambda k: k["x"])
            
            # INFERENCE: If Price is missing but Stock/Profit exists, assume Price is left of Stock
            types_found = {h["type"] for h in header_tokens}
            if "price" not in types_found and "stock" in types_found:
                stock_idx = next(i for i, h in enumerate(header_tokens) if h["type"] == "stock")
                stock_h = header_tokens[stock_idx]
                virtual_price = {"type": "price", "x": stock_h["x"] - 0.15, "x_min": stock_h["x_min"] - 0.15, "x_max": stock_h["x_min"] - 0.02}
                header_tokens.insert(stock_idx, virtual_price)
                
            for i, h in enumerate(header_tokens):
                if i == 0:
                    start = max(0.20, h["x_min"] - 0.10) 
                else:
                    prev = header_tokens[i-1]
                    start = (prev["x_max"] + h["x_min"]) / 2
                
                if i == len(header_tokens) - 1:
                    end = 1.0
                else:
                    nxt = header_tokens[i+1]
                    end = (h["x_max"] + nxt["x_min"]) / 2
                    
                col_zones[h["type"]] = (start, end)
                
            print("📐 GEOMETRIC HEADERS FOUND (DISJOINT):", col_zones)

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
                if t["text"].isdigit() and len(t["text"]) == 13 and val > 1000000:
                    continue

                matched_zone = False
                
                # Check Zones First
                if "qty" in col_zones:
                    if col_zones["qty"][0] <= t_center <= col_zones["qty"][1]:
                        if (isinstance(val, int) or (isinstance(val, float) and val.is_integer())) and exact_qty is None:
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
            
            # 5️⃣ WIDEST SCOPE FALLBACK
            # if zones failed (e.g. headers missing), blind fill from unused numbers
            if exact_qty is None:
                # Try to find a small integer < 500
                for n in unused_numbers:
                     if (isinstance(n, int) or n.is_integer()) and n < 500:
                         exact_qty = int(n)
                         unused_numbers.remove(n)
                         break
            
            if exact_price is None:
                # Take the first float remaining (typically Unit Price comes before Total)
                for n in unused_numbers:
                    exact_price = n
                    unused_numbers.remove(n)
                    break
            
            # If we still have numbers, maybe one is total
            if exact_total is None and unused_numbers:
                 exact_total = unused_numbers[0] # Next number is likely total


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
