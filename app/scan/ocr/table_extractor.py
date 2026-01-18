import re
from typing import List

from app.scan.models.document_line_item import (
    DocumentLineItem,
    DocumentToken,
)

TOKEN_RE = re.compile(
    r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\b\d{1,2}\b"
)


def extract_table_items(document) -> List[DocumentLineItem]:

    items: List[DocumentLineItem] = []

    for page_idx, page in enumerate(document.pages):
        print(f"TABLE COUNT (page {page_idx}):", len(page.tables))

        for table in page.tables:
            # 1️⃣ SEMANTIC HEADER ANALYSIS
            col_map = {
                "qty": -1,
                "price": -1,
                "total": -1,
                "profit": -1,
                "cost": -1
            }
            
            # Check header rows
            rows_to_scan = list(table.header_rows)
            if table.body_rows:
                rows_to_scan.append(table.body_rows[0])
            
            for h_row in rows_to_scan:
                for col_idx, cell in enumerate(h_row.cells):
                    txt = _get_text(document, cell.layout.text_anchor).upper()
                    
                    # QTY
                    if any(x in txt for x in ["ADET", "MİKTAR", "SATILAN", "SAT.AD"]):
                        if "STOK" not in txt and "MEVCUT" not in txt:
                            col_map["qty"] = col_idx

                    # PRICE (Birim Fiyat)
                    if any(x in txt for x in ["FİYAT", "FIYAT", "BİRİM", "BIRIM"]):
                        if "TOPLAM" not in txt and "TUTAR" not in txt:
                             col_map["price"] = col_idx

                    # TOTAL (Tutar)
                    if any(x in txt for x in ["TUTAR", "TOPLAM", "NET SATIŞ", "CİRO"]):
                        # Avoid "KDV TUTAR" or "ISK TUTAR" logic if simplified
                         col_map["total"] = col_idx

                    # PROFIT (Kar)
                    if any(x in txt for x in ["KAR", "KÂR", "KAZANÇ", "ECZ"]):
                        if "ECZANE" not in txt:
                             col_map["profit"] = col_idx

                    # COST (Maliyet)
                    if any(x in txt for x in ["MALİYET", "MALIYET", "ALIS", "ALIŞ", "GELİŞ", "GELIS"]):
                         col_map["cost"] = col_idx

                    # STOCK (Stok)
                    if any(x in txt for x in ["STOK", "MEVCUT", "KALAN", "ELDEKİ"]):
                         col_map["stock"] = col_idx
                
                # If we found at least 2 key columns, stop scanning
                if sum(1 for v in col_map.values() if v != -1) >= 2:
                    break
            
            print(f"🔍 DEBUG: Header Scan Complete")
            # print(f"   Headers Scanned: {[cell._get_text(document, cell.layout.text_anchor) for h in rows_to_scan for cell in h.cells]}") 
            print(f"📊 COLUMN MAP: {col_map}")

            for row in table.body_rows:
                raw_parts: List[str] = []
                tokens: List[DocumentToken] = []
                
                # Extracted values
                extracted = {k: None for k in col_map.keys()}
                # Update extraction map with 'stock' if not present in init
                if "stock" not in extracted: extracted["stock"] = None

                for col_idx, cell in enumerate(row.cells):
                    cell_text = _get_text(
                        document,
                        cell.layout.text_anchor
                    )

                    if not cell_text:
                        continue
                    
                    cell_text = cell_text.strip()
                    raw_parts.append(cell_text)
                    
                    # 2️⃣ EXACT COLUMN EXTRACTION
                    for key, target_idx in col_map.items():
                        if col_idx == target_idx:
                            # Clean and parse number
                            # Handles "1.234,56", "1234.56", "1"
                            # Simple regex for number finding
                            nums = re.findall(r"[\d.,]+", cell_text)
                            if nums:
                                # Try parsing the longest candidate as the value
                                candidate = max(nums, key=len)
                                try:
                                    # Normalize TR Format
                                    if "," in candidate:
                                        val = float(candidate.replace(".", "").replace(",", "."))
                                    else:
                                        val = float(candidate)
                                    
                                    # Filter weird values
                                    if key == "qty" or key == "stock":
                                        extracted[key] = int(val)
                                    else:
                                        extracted[key] = val
                                except:
                                    pass

                    verts = cell.layout.bounding_poly.normalized_vertices
                    xs = [v.x for v in verts if v.x is not None]
                    if not xs:
                        continue

                    min_x = min(xs)
                    max_x = max(xs)
                    mid_x = round((min_x + max_x) / 2, 3)

                    parts = TOKEN_RE.findall(cell_text)
                    if not parts:
                        parts = cell_text.split()

                    for part in parts:
                        fake_layout = cell.layout
                        fake_layout.bounding_poly.normalized_vertices = [
                            type(verts[0])(x=mid_x, y=v.y)
                            for v in verts
                        ]

                        tokens.append(
                            DocumentToken(
                                text=part.strip(),
                                layout=fake_layout
                            )
                        )

                if not raw_parts:
                    continue
                
                # 🛑 BARCODE MANDATE (STRICT MODE)
                # Filter out rows that don't have a 13-digit barcode
                has_barcode = any(token.text.isdigit() and len(token.text) == 13 for token in tokens)
                if not has_barcode:
                    # Skip noise lines like headers/footers explicitly
                    continue

                item = DocumentLineItem(
                    raw_text=" | ".join(raw_parts),
                    tokens=tokens,
                    source="TABLE",
                    confidence=0.95,
                )
                item.exact_quantity_match = extracted.get("qty")
                item.exact_price_match = extracted.get("price")
                item.exact_total_match = extracted.get("total")
                item.exact_profit_match = extracted.get("profit")
                item.exact_cost_match = extracted.get("cost")
                item.exact_stock_match = extracted.get("stock")

                items.append(item)

    return items



def _get_text(document, anchor):
    text = ""
    for seg in anchor.text_segments:
        start = seg.start_index or 0
        end = seg.end_index
        text += document.text[start:end]
    return text.strip()
