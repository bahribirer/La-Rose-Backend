from typing import List, Optional


class DocumentToken:
    def __init__(self, text: str, layout):
        self.text = text
        self.layout = layout


class DocumentLineItem:
    def __init__(
        self,
        raw_text: str,
        tokens: Optional[List[DocumentToken]] = None,
        source: str = "TABLE",
        confidence: float = 1.0,
    ):
        self.raw_text = raw_text
        self.tokens = tokens or []
        self.source = source
        self.confidence = confidence

        # parsed fields
        self.barcode: Optional[str] = None
        self.product_name: Optional[str] = None
        self.quantity: int = 1
        self.unit_price: Optional[float] = None
        self.line_total: Optional[float] = None
        self.ecz_kar: Optional[float] = None
        self.maliyet: Optional[float] = None
        
        # 🔥 SMART TABLE PARSING
        self.quantity_candidates: List[int] = []  # All integers in row
        self.exact_quantity_match: Optional[int] = None  # From specific column
