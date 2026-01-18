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
        # Google Document AI v1: tokens are usually a flat list on the page
        # Fallback: if tokens not found, try visual_elements or lines?
        # Let's hope 'tokens' is available. 
        # If not, we can use lines -> segments, but tokens is standard for "words".
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
        
        rows = []
        current_row = []
        if all_tokens:
            current_y = all_tokens[0]["y"]
            
            for t in all_tokens:
                # If Y diff is small (< 0.01 approx for normalized coords), same row
                if abs(t["y"] - current_y) < 0.015: 
                    current_row.append(t)
                else:
                    # New row
                    # Sort current row by X
                    current_row.sort(key=lambda k: k["x"])
                    rows.append(current_row)
                    current_row = [t]
                    current_y = t["y"]
            
            if current_row:
                current_row.sort(key=lambda k: k["x"])
                rows.append(current_row)

        # 3️⃣ Detect Headers & Define Column Zones (X-Ranges)
        col_zones = {} # "qty": (x_min, x_max), "total": ...
        
        for row in rows:
            row_text = " ".join([t["text"].upper() for t in row])
            
            # Heuristic: Check for Header keywords
            if "BARKOD" in row_text or "URUN ADI" in row_text or "FIYAT" in row_text:
                for t in row:
                    txt = t["text"].upper()
                    if "ADET" in txt or "MIKTAR" in txt or "SAT.AD" in txt:
                        if "STOK" not in txt:
                            # Found Qty Header
                             col_zones["qty"] = (t["x_min"] - 0.02, t["x_max"] + 0.02)
                    
                    if "TUTAR" in txt or "TOPLAM" in txt:
                        col_zones["total"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)
                        
                    if "FIYAT" in txt or "BIRIM" in txt:
                         col_zones["price"] = (t["x_min"] - 0.05, t["x_max"] + 0.05)
                
                # If we found headers, stop scanning
                if col_zones:
                    print("📐 GEOMETRIC HEADERS FOUND:", col_zones)
                    break
        
        # 4️⃣ Extract Data from Rows using Column Zones
        for row in rows:
            raw_text = " ".join([t["text"] for t in row])
            
            # Skip header rows or irrelevant text
            if "TOPLAM" in raw_text.upper() or "SAYFA" in raw_text.upper():
                continue
            
            # Identify Barcode (start of a product line)
            # Simple check: First or second token looks like barcode
            # Or just store everything and let the mapper filter by barcode later.
            
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
            # We construct a synthetic one
            item = DocumentLineItem(
                raw_text=raw_text,
                confidence=0.90,
                source="GEOMETRY"
            )
            item.exact_quantity_match = exact_qty
            item.exact_total_match = exact_total
            item.exact_price_match = exact_price
            
            # Pass all tokens? or just raw text?
            # Mapper uses raw text for regex if exact match is missing.
            # So raw_text is populated.
            
            items.append(item)

    return items


def _parse_number(text: str):
    clean = text.replace(".", "").replace(",", ".")
    try:
        if "," in text or "." in text: 
            return float(clean)
        return int(clean)
    except:
        return None

def _get_text(document, anchor):
    text = ""
    for seg in anchor.text_segments:
        start = seg.start_index or 0
        end = seg.end_index
        text += document.text[start:end]
    return text.strip()
