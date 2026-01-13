from typing import Dict, Any, List

from app.sales.schemas import SaleItemFromScan
from app.scan.strategy.base import ReportStrategy
from app.scan.ocr.line_extractor import extract_lines
from app.scan.ocr.table_extractor import extract_table_items
from app.scan.ocr.document_ai_layout_reader import read_with_layout_parser

from app.scan.parsers.barcode_product_parser import (
    extract_barcode,
    normalize_barcode,
)

from app.scan.utils.price_extract import extract_prices_from_lines
from app.scan.parsers.table_line_parser import parse_table_line
from app.scan.mappers.table_item_to_sale_item import table_item_to_sale_item

from app.scan.normalizers.product_total_normalizer import (
    normalize_product_total_prices
)


class ProductTotalStrategy(ReportStrategy):
    name = "PRODUCT_TOTAL"

    def parse(
        self,
        document,
        product_map: Dict[str, dict],
        table_hint: bool = False,
    ) -> Dict[str, Any]:

        print("🟢 Using ProductTotalStrategy (HYBRID MODE)")

        # ==================================================
        # 1️⃣ TABLE MODE – DOCUMENT OCR
        # ==================================================
        table_items = extract_table_items(document)

        if table_items:
            print(f"📊 TABLE ITEMS FOUND (OCR): {len(table_items)}")

        # ==================================================
        # 2️⃣ TABLE MODE – LAYOUT PARSER (FALLBACK)
        # ==================================================
        if not table_items and table_hint:
            print("🧪 TRYING LAYOUT PARSER")

            file_path = getattr(document, "file_path", None)
            if file_path:
                layout_doc = read_with_layout_parser(file_path)
                table_items = extract_table_items(layout_doc)

                if table_items:
                    print(
                        f"📊 TABLE ITEMS FOUND (LAYOUT): "
                        f"{len(table_items)}"
                    )

        # ==================================================
        # 3️⃣ TABLE MODE SUCCESS
        # ==================================================
        if table_items:
            parsed_items = [
                parse_table_line(i)
                for i in table_items
                if i.raw_text
            ]

            sale_items: List[SaleItemFromScan] = []

            for item in parsed_items:
                sale = table_item_to_sale_item(item, product_map)
                if sale:
                    sale_items.append(sale)

            if sale_items:
                print("✅ PRODUCT_TOTAL → TABLE MODE SUCCESS")
                return {
                    "items": sale_items,
                    "_meta": {
                        "used_table": True
                    },
                }

            print("⚠️ TABLE PARSED BUT NO SALE ITEMS → BLOCK MODE")

        else:
            print("ℹ️ NO TABLE FOUND → BLOCK MODE")

        # ==================================================
        # 4️⃣ BLOCK MODE (FALLBACK)
        # ==================================================
        lines = extract_lines(document)

        barcodes: List[str] = []

        for line in lines:
            raw = extract_barcode(line)
            if not raw:
                continue

            code = normalize_barcode(raw)
            if code and code in product_map:
                barcodes.append(code)

        print(f"🧠 FOUND {len(barcodes)} PRODUCTS (BLOCK MODE)")

        if not barcodes:
            return {"items": []}

        prices = extract_prices_from_lines(lines)
        print(f"🧠 FOUND {len(prices)} PRICES (BLOCK MODE)")

        if not prices:
            return {"items": []}

        columns = round(len(prices) / len(barcodes))

        if columns < 4 or columns > 8:
            print(
                f"⚠️ UNEXPECTED COLUMN COUNT ({columns}), "
                f"FALLING BACK TO 5"
            )
            columns = 5

        print(f"📐 PRICE COLUMNS PER PRODUCT: {columns}")

        items: List[SaleItemFromScan] = []

        for idx, barcode in enumerate(barcodes):
            base = idx * columns
            block = prices[base: base + columns]

            if len(block) < columns:
                print(f"⚠️ PRICE BLOCK MISSING FOR {barcode}")
                continue

            product = product_map[barcode]

            # 🔥 FİYAT SEMANTİĞİ ÇÖZ
            unit_price, maliyet, ecz_kar, tutar = (
                normalize_product_total_prices(
                    floats=block,
                    quantity=1,
                )
            )

            print(f"""
🧪 BLOCK MODE PRICE MAP
  🔹 Barcode     : {barcode}
  🔹 Raw Prices  : {block}
  🔹 Unit Price  : {unit_price}
  🔹 Total       : {tutar}
  🔹 Cost        : {maliyet}
  🔹 Profit      : {ecz_kar}
""")

            items.append(
    SaleItemFromScan(
        urun_id=barcode,
        urun_name=product.get("tr_name") or product.get("name"),
        miktar=1,

        # 🔥 ADMIN FIELDS (EKSİK OLANLAR)
        birim_fiyat=unit_price,
        tutar=tutar,

        # 🔥 FİNANS
        maliyet=maliyet,
        ecz_kar=ecz_kar,

        match_confidence=0.95,
    )
)


        print(f"✅ PRODUCT_TOTAL → BLOCK MODE SUCCESS ({len(items)} items)")

        return {
            "items": items
        }
