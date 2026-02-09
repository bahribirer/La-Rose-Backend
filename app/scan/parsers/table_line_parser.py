# app/scan/parsers/table_line_parser.py
import re
from app.scan.parsers.barcode_product_parser import BARCODE_RE

# Flex regex: 1.234,56 | 1234.56 | 123.4 | 123
PRICE_RE = re.compile(
    r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?"
)

def normalize_tr_price(v: str) -> float:
    v = v.strip()
    if not v: return 0.0
    
    # Smart detection for US vs TR format
    # Case 1: Both separators exist (e.g., 1,234.56 or 1.234,56)
    if "." in v and "," in v:
        last_dot = v.rfind(".")
        last_comma = v.rfind(",")
        if last_dot > last_comma:
            # US Format: 1,234.56 -> Remove comma, keep dot
            return float(v.replace(",", ""))
        else:
            # TR Format: 1.234,56 -> Remove dot, replace comma with dot
            return float(v.replace(".", "").replace(",", "."))
            
    # Case 2: Only Dot (e.g., 123.45 or 1.234)
    elif "." in v:
        # Ambiguous: 1.234 could be 1234 or 1.234
        # Heuristic: If it has 2 decimal places, assume decimal (common in currency)
        # Or if the report seems to use dots as decimals elsewhere.
        # Given the "Price 0" bug, assuming dot-as-decimal determines the fix for "880.00" -> 880.0
        return float(v)
        
    # Case 3: Only Comma (e.g., 123,45)
    elif "," in v:
        return float(v.replace(",", "."))
        
    return float(v)

def parse_table_line(item):
    print("\n🧩 PARSING LINE:", item.raw_text[:100] if item.raw_text else "?")

    # Preserve entity exact matches — only init if not set
    if not hasattr(item, 'raw_prices') or item.raw_prices is None:
        item.raw_prices = []
    else:
        item.raw_prices = item.raw_prices  # keep existing
    
    if not hasattr(item, 'quantity_candidates') or item.quantity_candidates is None:
        item.quantity_candidates = []
    
    if not hasattr(item, 'barcode') or not item.barcode:
        item.barcode = None

    # If entity already has exact matches, skip token parsing
    has_exact = (
        getattr(item, 'exact_quantity_match', None) is not None
        and (getattr(item, 'exact_total_match', None) is not None 
             or getattr(item, 'exact_price_match', None) is not None)
    )
    
    if has_exact and item.barcode:
        print(f"   ✅ ENTITY EXACT MATCH: barcode={item.barcode}, qty={item.exact_quantity_match}")
        return item

    # BARCODE (from tokens)
    if item.tokens:
        for token in item.tokens:
            if BARCODE_RE.fullmatch(token.text):
                item.barcode = token.text
                print("   🧾 BARCODE:", item.barcode)
                break

    # TOKENS → prices and quantity candidates
    if item.tokens:
        item.raw_prices = []
        item.quantity_candidates = []
        for token in item.tokens:
            raw = token.text.strip()

            # adet
            if raw.isdigit():
                val = int(raw)
                if 0 < val <= 500:
                    item.quantity_candidates.append(val)
                    print("   🔢 CANDIDATE QTY:", val)
                continue

            # fiyat
            if PRICE_RE.fullmatch(raw):
                price = normalize_tr_price(raw)
                item.raw_prices.append(price)
                print("   💰 PRICE:", price)

    return item
