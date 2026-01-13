from typing import List, Dict, Any

from app.scan.strategy.base import ReportStrategy
from app.scan.ocr.line_extractor import extract_lines
from app.scan.parsers.barcode_product_parser import normalize_barcode
from app.scan.utils.price_semantics import infer_price_semantics
from app.sales.schemas import SaleItemFromScan


class ReceiptStrategy(ReportStrategy):
    name = "RECEIPT"

    def parse(
        self,
        document,
        product_map: Dict[str, dict],
        table_hint: bool = False,
    ) -> Dict[str, Any]:

        print("🧾 Using ReceiptStrategy")

        lines: List[str] = extract_lines(document)

        counters: Dict[str, SaleItemFromScan] = {}

        i = 0
        n = len(lines)

        while i < n:
            raw = lines[i].strip()
            barcode = normalize_barcode(raw)

            if not barcode or barcode not in product_map:
                i += 1
                continue

            product = product_map[barcode]
            i += 1

            numbers: List[float] = []
            qty_candidates: List[int] = []

            while i < n:
                token = lines[i].strip()

                if normalize_barcode(token):
                    break

                if token.isdigit():
                    val = int(token)
                    if 0 < val <= 20:
                        qty_candidates.append(val)

                if any(c.isdigit() for c in token):
                    try:
                        numbers.append(float(token.replace(",", "")))
                    except:
                        pass

                i += 1

            qty = qty_candidates[0] if qty_candidates else 1

            _, _, _, tutar = infer_price_semantics(
                floats=numbers,
                quantity=qty,
            )

            print(f"""
🧾 RECEIPT PARSED
  🔹 Barkod : {barcode}
  🔹 Qty    : {qty}
  🔹 Tutar  : {tutar}
""")

            if barcode not in counters:
                counters[barcode] = SaleItemFromScan(
                    urun_id=barcode,
                    urun_name=product.get("tr_name") or product.get("name"),
                    miktar=qty,
                    maliyet=None,
                    ecz_kar=None,
                    match_confidence=0.75,
                )
            else:
                counters[barcode].miktar += qty

        return {
            "items": list(counters.values())
        }
