from app.sales.schemas import SaleItemFromScan
from app.scan.normalizers.product_total_normalizer import (
    normalize_product_total_prices,
)


def table_item_to_sale_item(item, product_map):
    if not item.barcode:
        return None

    product = product_map.get(item.barcode)
    if not product:
        return None

    # 🔥 STRUCTURAL PRIORITY
    candidates = item.quantity_candidates
    if item.exact_quantity_match:
        # If we found a quantity in the specific "Adet" column, prioritize it!
        # But verify it with Smart Math logic inside normalizer.
        candidates = [item.exact_quantity_match] + [c for c in candidates if c != item.exact_quantity_match]

    # 🔥 OCR'dan gelen fiyatları semantik olarak ayır
    unit_price, maliyet, ecz_kar, tutar, selected_qty = normalize_product_total_prices(
        floats=item.raw_prices,
        candidate_quantities=candidates,
    )
    print("""
🧪 TABLE ITEM → SALE ITEM
  🔹 Barcode      : {}
  🔹 Quantity     : {} (Selected)
  🔹 Raw Prices   : {}
  🔹 Unit Price   : {}
  🔹 Total Price  : {}
  🔹 Cost         : {}
  🔹 Profit       : {}
""".format(
    item.barcode,
    selected_qty,
    item.raw_prices,
    unit_price,
    tutar,
    maliyet,
    ecz_kar,
))


    return SaleItemFromScan(
        urun_id=item.barcode,
        urun_name=product.get("tr_name") or product.get("name"),
        miktar=selected_qty,

        # 🔥 ADMIN-ONLY FIELDS
        birim_fiyat=unit_price,
        tutar=tutar,

        # mevcut finansal alanlar
        maliyet=maliyet,
        ecz_kar=ecz_kar,

        match_confidence=1.0,
    )
