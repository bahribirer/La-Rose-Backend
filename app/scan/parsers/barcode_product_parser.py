import re
from typing import List, Dict, Optional, Tuple

from app.sales.schemas import SaleItemFromScan

# EAN-13 – 3 ile başlayan barkod
BARCODE_RE = re.compile(r"\b3\d{12}\b")


# ===================== EXTRACT =====================

def extract_barcode(text: str) -> Optional[str]:
    """
    Satır içinde 3xxxxxxxxxxxx (13 hane) arar.
    Bulursa döner.
    """
    m = BARCODE_RE.search(text or "")
    return m.group(0) if m else None


# ===================== NORMALIZE =====================

def normalize_barcode(raw: str) -> Optional[str]:
    """
    OCR'dan gelen barkodu normalize eder.
    """
    digits = "".join(c for c in (raw or "") if c.isdigit())

    if len(digits) < 8:
        return None

    # OCR bazen başına tarih/fiş no ekler → son 13
    if len(digits) > 13:
        digits = digits[-13:]

    # baştaki fazla 0 / 1 temizle
    if digits.startswith(("0", "1")) and len(digits) == 13:
        digits = digits[1:]

    if len(digits) != 13:
        return None

    # sadece 3 ile başlayan EAN-13
    if not digits.startswith("3"):
        return None

    return digits


# ===================== EAN-13 CHECK DIGIT =====================

def ean13_check_digit(first12: str) -> int:
    if len(first12) != 12 or not first12.isdigit():
        return -1

    s = 0
    for i, ch in enumerate(first12):
        d = int(ch)
        if i % 2 == 0:
            s += d
        else:
            s += 3 * d
    return (10 - (s % 10)) % 10


def fix_check_digit(code: str) -> Optional[str]:
    if len(code) != 13 or not code.isdigit():
        return None
    cd = ean13_check_digit(code[:12])
    if cd < 0:
        return None
    return code[:12] + str(cd)


# ===================== MATCH =====================

def match_barcode_safely(
    barcode: str,
    product_map: Dict[str, dict],
) -> Tuple[Optional[str], float]:
    """
    Returns: (matched_barcode, confidence)
    """
    if barcode in product_map:
        return barcode, 1.0

    fixed = fix_check_digit(barcode)
    if fixed and fixed in product_map:
        return fixed, 0.92

    return None, 0.0


# ===================== FALLBACK PARSER =====================

def parse_barcode_products_to_sale_items(
    lines: List[str],
    product_map: Dict[str, dict],
) -> List[SaleItemFromScan]:
    """
    TABLE mode yoksa kullanılır.
    SADECE quantity sayar.
    """

    counters: Dict[str, SaleItemFromScan] = {}

    for line in lines:
        # satır içinde barkod ara
        raw = extract_barcode(line)
        if not raw:
            continue

        barcode = normalize_barcode(raw)
        if not barcode:
            continue

        matched, conf = match_barcode_safely(barcode, product_map)
        if not matched:
            continue

        if matched not in counters:
            product = product_map[matched]
            counters[matched] = SaleItemFromScan(
                urun_id=product["id"],
                urun_name=product.get("tr_name") or product.get("name"),
                miktar=1,
                maliyet=product.get("cost", 0.0),
                ecz_kar=None,
                match_confidence=conf,
            )
        else:
            counters[matched].miktar += 1

    return list(counters.values())
