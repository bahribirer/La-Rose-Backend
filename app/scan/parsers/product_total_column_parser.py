import re
from typing import List, Dict
from app.sales.schemas import SaleItemFromScan
from app.scan.parsers.barcode_product_parser import normalize_barcode

PRICE_RE = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?")


def parse_product_total_columnar(
    lines: List[str],
    product_map: Dict[str, dict],
) -> List[SaleItemFromScan]:

    barcodes: List[str] = []
    totals: List[float] = []

    # 1️⃣ Barkodları sırayla topla
    for line in lines:
        bc = normalize_barcode(line)
        if bc and bc in product_map:
            barcodes.append(bc)

    # 2️⃣ Satış tutarlarını topla
    for line in lines:
        if PRICE_RE.fullmatch(line.strip()):
            try:
                val = float(line.replace(",", ""))
                if val > 100:  # küçük KDV vs ele
                    totals.append(val)
            except:
                pass

    print("🧠 COLUMN MODE")
    print("  🔹 Barkodlar :", barcodes)
    print("  🔹 Tutarlar  :", totals)

    # 3️⃣ Index bazlı eşleştir
    items: List[SaleItemFromScan] = []

    for i in range(min(len(barcodes), len(totals))):
        bc = barcodes[i]
        product = product_map[bc]

        items.append(
            SaleItemFromScan(
                urun_id=product["id"],
                urun_name=product.get("tr_name") or product.get("name"),
                miktar=1,
                maliyet=None,
                ecz_kar=None,
                match_confidence=0.9,
            )
        )

    return items
