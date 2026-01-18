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
            # 1️⃣ HEADER ANALYSIS
            qty_col_idx = -1
            
            # Check header rows
            rows_to_scan = list(table.header_rows)
            
            # 🔥 FALLBACK: If header missing, check the first body row too
            if table.body_rows:
                rows_to_scan.append(table.body_rows[0])

            # Let's trust Document AI structure first.
            
            for h_row in rows_to_scan:
                for col_idx, cell in enumerate(h_row.cells):
                    txt = _get_text(document, cell.layout.text_anchor).upper()
                    # Keywords for Sold Quantity
                    if any(x in txt for x in ["ADET", "MİKTAR", "SATILAN", "SAT.AD"]):
                        # Avoid "STOK ADET" or "KDV ADET"
                        if "STOK" in txt or "MEVCUT" in txt:
                            continue
                        qty_col_idx = col_idx
                        print(f"🎯 FOUND QTY COLUMN at index {col_idx}: {txt}")
                        break
                if qty_col_idx != -1:
                    break

            for row in table.body_rows:
                raw_parts: List[str] = []
                tokens: List[DocumentToken] = []
                
                exact_qty = None

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
                    if col_idx == qty_col_idx:
                        # Try to extract integer from this specific cell
                        # Sometimes cell has "1 Adet" or "1"
                        nums = re.findall(r"\b\d+\b", cell_text)
                        if nums:
                            try:
                                val = int(nums[0]) # First int in the strictly identified column
                                if 0 < val < 1000:
                                    exact_qty = val
                                    print(f"   🎯 EXACT QTY DETECTED: {val} (from Col {col_idx})")
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
                
                item = DocumentLineItem(
                    raw_text=" | ".join(raw_parts),
                    tokens=tokens,
                    source="TABLE",
                    confidence=0.95,
                )
                item.exact_quantity_match = exact_qty
                items.append(item)

    return items



def _get_text(document, anchor):
    text = ""
    for seg in anchor.text_segments:
        start = seg.start_index or 0
        end = seg.end_index
        text += document.text[start:end]
    return text.strip()
