import re
from typing import List

from app.scan.models.document_line_item import (
    DocumentLineItem,
    DocumentToken,
)

TOKEN_RE = re.compile(
    r"\d{1,3}(?:\.\d{3})*,\d{2}|\b\d{1,2}\b"
)


def extract_table_items(document) -> List[DocumentLineItem]:

    items: List[DocumentLineItem] = []

    for page_idx, page in enumerate(document.pages):
        print(f"TABLE COUNT (page {page_idx}):", len(page.tables))

        for table in page.tables:
            for row in table.body_rows:
                raw_parts: List[str] = []
                tokens: List[DocumentToken] = []

                for cell in row.cells:
                    cell_text = _get_text(
                        document,
                        cell.layout.text_anchor
                    )

                    if not cell_text:
                        continue

                    cell_text = cell_text.strip()
                    raw_parts.append(cell_text)

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

                items.append(
                    DocumentLineItem(
                        raw_text=" | ".join(raw_parts),
                        tokens=tokens,
                        source="TABLE",
                        confidence=0.95,
                    )
                )

    return items



def _get_text(document, anchor):
    text = ""
    for seg in anchor.text_segments:
        start = seg.start_index or 0
        end = seg.end_index
        text += document.text[start:end]
    return text.strip()
