import re
from typing import List, Dict

from app.sales.schemas import SaleItemFromScan
from app.scan.parsers.barcode_product_parser import normalize_barcode

PRICE_RE = re.compile(r"\d{1,3}(?:,\d{3})*(?:\.\d+)?")


def parse_product_total_line_blocks(
    lines: List[str],
    product_map: Dict[str, dict],
) -> List[SaleItemFromScan]:

    items: List[SaleItemFromScan] = []

    i = 0
    n = len(lines)

    while i < n:
        line = lines[i].strip()

        # 1️⃣ Barkod aynı satırda olabilir
        barcode = normalize_barcode(line)
        if not barcode or barcode not in product_map:
            i += 1
            continue

        product = product_map[barcode]
        i += 1

        prices: List[float] = []

        # 2️⃣ Bu barkoda ait SATIR BLOĞUNU oku
        while i < n:
            token = lines[i].strip()

            # yeni barkod → blok bitti
            if normalize_barcode(token):
                break

            # footer guard
            if token.upper().startswith("TOPLAM"):
                break

            for m in PRICE_RE.findall(token):
                try:
                    prices.append(float(m.replace(",", "")))
                except:
                    pass

            i += 1

        if not prices:
            continue

        # 3️⃣ Satış Tutarı = en büyük ama "aşırı büyük" olmayan
        prices_sorted = sorted(prices)

        # genelde ürün satış tutarı,
        # blok içindeki max ama tüm rapor toplamı değil
        tutar = prices_sorted[-1]

        # güvenlik: uçuk büyükse (genel toplam)
        if tutar > 100_000:
            continue

        print(f"""
🧾 PRODUCT TOTAL PARSED
  🔹 Barkod : {barcode}
  🔹 Tutar  : {tutar}
""")

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
