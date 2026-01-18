import re
from typing import List, Dict, Union

from app.sales.schemas import SaleItemFromScan
from app.scan.parsers.barcode_product_parser import normalize_barcode
from app.scan.normalizers.product_total_normalizer import (
    normalize_product_total_prices
)

PRICE_RE = re.compile(
    r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+\.\d+|\d+,\d+"
)
INT_RE = re.compile(r"^\d+$")


def is_footer_line(s: str) -> bool:
    """
    Footer satırlarını yakala ama 'TOPLAMLARI' gibi başlıkları yakalama.
    Sadece satır başında 'TOPLAM' vb. varsa footer say.
    """
    t = s.strip().upper()
    return (
        t.startswith("TOPLAM")
        or t.startswith("GENEL TOPLAM")
        or t.startswith("TOPLAMI")
        or t.startswith("TOTAL")
    )


def parse_line_based_sales_report(
    lines: List[str],
    product_map: Dict[str, dict],
) -> List[SaleItemFromScan]:
    items: List[SaleItemFromScan] = []

    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i].strip()

        # ✅ FOOTER GUARD (başlık TOPLAMLARI'na takılmasın)
        if is_footer_line(raw):
            break

        # 1️⃣ Barkod → yeni ürün başlangıcı
        barcode = normalize_barcode(raw)
        if not barcode:
            i += 1
            continue

        product = product_map.get(barcode)
        if not product:
            i += 1
            continue

        # 2️⃣ Barkoddan sonraki sayıları topla
        numbers: List[Union[int, float]] = []

        # 🚨 FIX: Current line might contain numbers too! Parse it first.
        # Remove barcode from raw string to avoid re-parsing it as a number (though regex handles it)
        # Just scan the whole line for numbers.
        current_tokens = raw.split()
        for token in current_tokens:
             if INT_RE.fullmatch(token) or PRICE_RE.fullmatch(token):
                if "," in token:
                     clean = token.replace(".", "").replace(",", ".")
                     val = float(clean)
                elif "." in token:
                     val = float(token)
                else:
                     val = int(token)
                
                # Avoid adding the barcode itself as a number if it looks like one (usually > 10 digits)
                if isinstance(val, int) and val > 1000000000:
                    continue
                    
                numbers.append(val)

        i += 1
        
        # 3️⃣ Continue scanning subsequent lines until next product
        while i < n:
            raw_line = lines[i].strip()

            # ✅ footer görünürse ürün bloğunu bitir
            if is_footer_line(raw_line):
                break

            # yeni barkod → yeni ürün
            if normalize_barcode(raw_line):
                break
            
            # 🔥 FIX: Tokenize the line! Don't treat "4 157.00" as one token.
            tokens_in_line = raw_line.split()
            
            for token in tokens_in_line:
                if INT_RE.fullmatch(token) or PRICE_RE.fullmatch(token):
                    if "," in token:
                        clean = token.replace(".", "").replace(",", ".")
                        val = float(clean)
                    elif "." in token:
                        val = float(token)
                    else:
                        val = int(token)
                    
                    # Avoid accidentally adding a barcode-like number
                    if isinstance(val, int) and val > 1000000000:
                        continue

                    numbers.append(val)

            i += 1

        # 3️⃣ Sayıları ayır
        ints = [x for x in numbers if isinstance(x, int)]
        floats = [x for x in numbers if isinstance(x, float)]

        # 4️⃣ Miktar Adayları
        valid_ints = [x for x in ints if x > 0]

        # 5️⃣ SEMANTIC PRICE INFERENCE & SMART QTY
        unit_price, maliyet, ecz_kar, tutar, selected_qty = normalize_product_total_prices(
            floats=floats,
            candidate_quantities=valid_ints,
        )


        # 6️⃣ Confidence (basit)
        confidence = 0.85
        if tutar is not None:
            confidence += 0.05
        if maliyet is not None:
            confidence += 0.05
        if ecz_kar is not None:
            confidence += 0.05
        confidence = round(confidence, 2)

        # 🧪 DEBUG
        print("\n🧾 PARSED PRODUCT DEBUG")
        print(f"  🔹 Barkod        : {barcode}")
        print(f"  🔹 Ürün Adı      : {product.get('tr_name') or product.get('name')}")
        print(f"  🔹 Ham Sayılar   : {numbers}")
        print(f"  🔹 Int'ler       : {ints}")
        print(f"  🔹 Float'lar     : {floats}")
        print(f"  🔹 Miktar        : {selected_qty} (Candidates: {valid_ints})")
        print(f"  🔹 Birim Fiyat   : {unit_price}")
        print(f"  🔹 Maliyet       : {maliyet}")
        print(f"  🔹 Ecz. Kar      : {ecz_kar}")
        print(f"  🔹 Tutar         : {tutar}")
        print(f"  🔹 Confidence    : {confidence}")

        items.append(
            SaleItemFromScan(
                urun_id=product["id"],
                urun_name=product.get("tr_name") or product.get("name"),
                miktar=selected_qty,
                maliyet=maliyet,
                ecz_kar=ecz_kar,
                match_confidence=confidence,
            )
        )

    return items
