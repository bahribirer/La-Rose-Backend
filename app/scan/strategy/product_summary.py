from typing import Dict, Any, Optional, List
from app.scan.strategy.base import ReportStrategy
from app.scan.ocr.line_extractor import extract_lines
from app.scan.parsers.barcode_product_parser import normalize_barcode


class ProductSummaryStrategy(ReportStrategy):
    name = "PRODUCT_SUMMARY"

    def parse(
        self,
        document,
        product_map: Dict[str, dict],
    ) -> Dict[str, Any]:

        print("🟡 Using ProductSummaryStrategy (BLOCK MODE)")

        lines = extract_lines(document)

        products: List[str] = []
        numbers: List[float] = []

        # 1️⃣ TÜM BARKODLARI TOPLA
        for line in lines:
            barcode = normalize_barcode(line.strip())
            if barcode and barcode in product_map:
                products.append(barcode)

        # 2️⃣ TÜM SAYILARI TOPLA
        for line in lines:
            for part in line.replace(",", "").split():
                try:
                    val = float(part)
                    if 100 <= val <= 200_000:
                        numbers.append(val)
                except:
                    pass

        items = []
        numbers.sort(reverse=True)

        for barcode in products:
            product = product_map[barcode]
            tutar: Optional[float] = numbers.pop(0) if numbers else None

            items.append(
                {
                    "urun_id": barcode,
                    "urun_name": product.get("tr_name") or product.get("name"),
                    "miktar": 1,
                    "tutar": tutar,
                    "confidence": 0.85 if tutar else 0.6,
                }
            )

        return {"items": items}
