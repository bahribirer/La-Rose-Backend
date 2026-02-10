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
        # 0️⃣ ENTITY MODE (CUSTOM PROCESSOR) - 🚀 PRIORITY 1
        # ==================================================
        from app.scan.ocr.entity_extractor import extract_items_from_entities
        entity_items = extract_items_from_entities(document)
        
        if entity_items:
            print(f"🚀 ENTITY ITEMS FOUND (CUSTOM AI): {len(entity_items)}")
            table_items = entity_items
        else:
            # ==================================================
            # 0.5️⃣ GROQ MODE (LLM REFINEMENT) - 🧠 PRIORITY 2
            # ==================================================
            # If Custom Entities fail, try Llama 3 on Raw Text
            from app.scan.ocr.groq_refiner import process_text_adaptive
            
            print("🧠 ATTEMPTING GROQ LLM REFINEMENT...")
            try:
                groq_data = process_text_adaptive(document.text)
                
                if groq_data and "urunler" in groq_data and groq_data["urunler"]:
                    print(f"✅ GROQ RETURNED {len(groq_data['urunler'])} ITEMS")
                    
                    # Convert Groq JSON to DocumentLineItem
                    from app.scan.models.document_line_item import DocumentLineItem
                    
                    groq_line_items = []
                    for p in groq_data["urunler"]:
                        # Map dynamic keys to fixed schema
                        # Normalize keys to lowercase
                        p_norm = {k.lower(): v for k, v in p.items()}
                        
                        barcode = str(p_norm.get("barkod") or "").strip()
                        # 🛑 STRICT: Only accept 13-digit EAN-13 barcodes starting with '3'
                        barcode_digits = "".join(c for c in barcode if c.isdigit())
                        if len(barcode_digits) != 13 or not barcode_digits.startswith("3"):
                            print(f"⚠️ GROQ: Skipping invalid barcode '{barcode}'")
                            continue
                        barcode = barcode_digits
                        
                        item = DocumentLineItem(raw_text=str(p), confidence=0.99)
                        item.barcode = barcode
                        
                        # Helper helpers
                        def to_float(x):
                            if not x: return 0.0
                            if isinstance(x, (float, int)): return float(x)
                            # Clean string: "1.234,50" -> 1234.50
                            clean = str(x).replace("TL", "").replace("₺", "").strip()
                            if "," in clean and "." in clean:
                                if clean.find(",") > clean.find("."): clean = clean.replace(".", "").replace(",", ".")
                            elif "," in clean: clean = clean.replace(",", ".")
                            try: return float(clean)
                            except: return 0.0

                        # Qty
                        q = p_norm.get("miktar") or p_norm.get("adet") or p_norm.get("satilan_adet") or p_norm.get("satis_adedi")
                        item.quantity = int(to_float(q)) if q else 1
                        item.exact_quantity_match = item.quantity

                        # Financials
                        item.exact_total_match = to_float(p_norm.get("toplam") or p_norm.get("tutar") or p_norm.get("satis_tutari") or p_norm.get("net_satis"))
                        item.exact_price_match = to_float(p_norm.get("fiyat") or p_norm.get("birim_fiyat") or p_norm.get("satis_fiyati"))
                        item.exact_stock_match = int(to_float(p_norm.get("stok") or p_norm.get("stok_mik") or p_norm.get("kalan")))
                        item.exact_cost_match = to_float(p_norm.get("maliyet") or p_norm.get("alis_fiyati"))
                        item.exact_profit_match = to_float(p_norm.get("kar") or p_norm.get("ecz_kar"))
                        
                        groq_line_items.append(item)
                    
                    if groq_line_items:
                        table_items = groq_line_items
                        print(f"🚀 GROQ ITEMS PARSED: {len(table_items)}")

            except Exception as e:
                print(f"⚠️ GROQ FAILED: {e}")

            if not table_items:
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

            print(f"🔄 Looping through {len(parsed_items)} parsed items...")
            for item in parsed_items:
                print(f"👉 Processing item: {item.barcode} | Raw: {item.raw_text[:20]}...")
                
                sale = table_item_to_sale_item(item, product_map)
                
                if sale:
                    print(f"✅ Mapper returned sale item for {item.barcode}")
                    sale_items.append(sale)
                else:
                    print(f"❌ Mapper returned None for {item.barcode}")

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
