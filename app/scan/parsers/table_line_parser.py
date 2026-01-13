# app/scan/parsers/table_line_parser.py
import re
from app.scan.parsers.barcode_product_parser import BARCODE_RE

PRICE_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")

def normalize_tr_price(v: str) -> float:
    return float(v.replace(".", "").replace(",", "."))

def parse_table_line(item):
    print("\n🧩 PARSING LINE:", item.raw_text)

    item.raw_prices = []
    item.quantity = None
    item.barcode = None

    # BARCODE
    for token in item.tokens:
        if BARCODE_RE.fullmatch(token.text):
            item.barcode = token.text
            print("   🧾 BARCODE:", item.barcode)
            break

    # TOKENS
    for token in item.tokens:
        raw = token.text.strip()

        # adet
        if raw.isdigit():
            val = int(raw)
            if 0 < val <= 500:
                item.quantity = val
                print("   🔢 QTY:", val)
            continue

        # fiyat
        if PRICE_RE.fullmatch(raw):
            price = normalize_tr_price(raw)
            item.raw_prices.append(price)
            print("   💰 PRICE:", price)

    return item
