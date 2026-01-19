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
        # 0️⃣ ENTITY MODE (CUSTOM PROCESSOR) - 🚀 PRIORITY
        # ==================================================
        from app.scan.ocr.entity_extractor import extract_items_from_entities
        entity_items = extract_items_from_entities(document)
        
        if entity_items:
            print(f"🚀 ENTITY ITEMS FOUND (CUSTOM AI): {len(entity_items)}")
            table_items = entity_items
        else:
            # ==================================================
            # 1️⃣ TABLE MODE – DOCUMENT OCR (FALLBACK)
            # ==================================================
            table_items = extract_table_items(document)

            if table_items:
                print(f"📊 TABLE ITEMS FOUND (OCR): {len(table_items)}")

        # ==================================================
        # 2️⃣ GEOMETRY MODE (MANUAL RECONSTRUCTION)
        # ==================================================
        if not table_items:
            print("🧪 TRYING GEOMETRY TABLE EXTRACTOR")
            from app.scan.ocr.geometry_table_extractor import extract_items_by_geometry
            
            geo_items = extract_items_by_geometry(document)
            if geo_items:
                print(f"📊 GEOMETRY ITEMS FOUND: {len(geo_items)}")
                table_items = geo_items
                
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
        # 4️⃣ BLOCK MODE (FALLBACK) -> NOW LINE MODE (ROBUST)
        # ==================================================
        # Fragile Block Mode replaced by Robust Line Parser
        from app.scan.parsers.line_report_parser import parse_line_based_sales_report
        
        lines = extract_lines(document)
        print(f"🧠 LINE MODE: Processing {len(lines)} lines")

        # Line-by-Line parser
        items = parse_line_based_sales_report(lines, product_map)

        if items:
            print(f"✅ PRODUCT_TOTAL → LINE MODE SUCCESS ({len(items)} items)")
            return {
                "items": items
            }

        print("⚠️ LINE MODE FAILED (No items found)")
        return {"items": []}
