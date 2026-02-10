from typing import List, Optional
from app.scan.models.document_line_item import DocumentLineItem

def extract_items_from_entities(document) -> List[DocumentLineItem]:
    """
    Extracts line items from Google Document AI 'Entities'.
    Used when a Custom Processor is configured (e.g. CDE Processor).
    """
    items: List[DocumentLineItem] = []
    
    # Check if document has entities
    if not hasattr(document, "entities") or not document.entities:
        print("⚠️ DOCUMENT HAS NO ENTITIES (Custom Processor returned 0 entities)")
        return []

    print(f"🧩 FOUND {len(document.entities)} ENTITIES")
    
    # DEBUG: Print all entity types to see what we got
    all_types = list(set([e.type_ for e in document.entities]))
    print(f"📋 AVAILABLE ENTITY TYPES: {all_types}")

    # Iterate over entities
    # The schema might be flat (barcode, qty...) or nested (LineItem -> barcode, qty...)
    # Based on user screenshot: 'items' is a Parent entity.
    
    parent_items = [e for e in document.entities if e.type_ in ["items", "Items", "line_item", "LineItem"]]
    
    if not parent_items:
        # Fallback: Maybe they are flat?
        # But user showed 'items' group.
        # Let's try to group them by vertical proximity if they are flat?
        # For now, assume hierarchical as shown.
        print("⚠️ No 'items' parent entity found. Checking for flat entities?")
        return []

    print(f"📦 FOUND {len(parent_items)} 'items' ROWS")

    for parent in parent_items:
        # Attributes are in parent.properties
        props = parent.properties
        
        data = {}
        for p in props:
            # Normalize keys
            key = p.type_
            val_text = p.mention_text
            val_norm = p.normalized_value.text if p.normalized_value else val_text
            
            data[key] = val_norm or val_text

        # Create DocumentLineItem
        # Map entity fields to our internal schema
        
        # Parse numbers
        def parse_float(v):
            if not v: return None
            # Handle 1.234,56 or 1,234.56
            # API normalized value is usually standard float string?
            # If not, use common parser
            clean = v.replace("TL", "").replace("₺", "").strip()
            # If it has comma as decimal: 12,50 -> 12.50
            # If it has dot as thousand: 1.200,50 -> 1200.50
            if "," in clean and "." in clean:
                if clean.find(",") > clean.find("."): # 1.234,56
                     clean = clean.replace(".", "").replace(",", ".")
                else: # 1,234.56
                     clean = clean.replace(",", "")
            elif "," in clean:
                clean = clean.replace(",", ".")
            
            try:
                return float(clean)
            except:
                return None

        # Helper for Qty
        def parse_int(v):
            f = parse_float(v)
            return int(f) if f else 1

        raw_barcode = data.get("barcode") or ""
        # 🛑 NORMALIZE: Strip whitespace, keep only digits
        barcode = "".join(c for c in str(raw_barcode) if c.isdigit())
        
        # Validate: must be 13-digit EAN-13 starting with '3'
        if len(barcode) != 13 or not barcode.startswith("3"):
            print(f"⚠️ ENTITY: Skipping invalid barcode '{raw_barcode}' → '{barcode}'")
            continue
        
        qty = parse_int(data.get("quantity"))
        
        # Financials
        unit_price = parse_float(data.get("unit_price"))
        total = parse_float(data.get("net_sales")) or parse_float(data.get("gross_sales")) or parse_float(data.get("total"))
        cost = parse_float(data.get("cost")) or parse_float(data.get("maliyet"))
        profit = parse_float(data.get("pharmacist_profit")) or parse_float(data.get("profit")) or parse_float(data.get("ecz_kar"))
        stock = parse_int(data.get("remaining_stock")) or parse_int(data.get("stock"))
        
        # Extended Financials
        discount = parse_float(data.get("discount_amount")) or parse_float(data.get("discount")) or parse_float(data.get("iskonto"))
        tax = parse_float(data.get("tax_amount")) or parse_float(data.get("tax")) or parse_float(data.get("vat_amount")) or parse_float(data.get("kdv"))
        gross_total = parse_float(data.get("gross_amount")) or parse_float(data.get("satis_tutari")) or parse_float(data.get("gross_sales"))

        print(f"✅ ENTITY ITEM: barcode={barcode}, qty={qty}, total={total}, price={unit_price}, disc={discount}, tax={tax}, gross={gross_total}")
        
        item = DocumentLineItem(raw_text=parent.mention_text, confidence=parent.confidence)
        item.barcode = barcode
        item.quantity = qty
        
        # Use 'Exact Match' fields to bypass heuristic mappers
        item.exact_quantity_match = qty
        item.exact_price_match = unit_price
        item.exact_total_match = total
        item.exact_cost_match = cost
        item.exact_profit_match = profit
        item.exact_stock_match = stock
        
        # Extended matches
        item.discount_amount = discount
        item.tax_amount = tax
        item.gross_total = gross_total
        
        items.append(item)

    return items
