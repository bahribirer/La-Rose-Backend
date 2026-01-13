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

    # 🔥 OCR'dan gelen fiyatları semantik olarak ayır
    unit_price, maliyet, ecz_kar, tutar = normalize_product_total_prices(
        floats=item.raw_prices,
        quantity=item.quantity or 1,
    )
    print("""
🧪 TABLE ITEM → SALE ITEM
  🔹 Barcode      : {}
  🔹 Quantity     : {}
  🔹 Raw Prices   : {}
  🔹 Unit Price   : {}
  🔹 Total Price  : {}
  🔹 Cost         : {}
  🔹 Profit       : {}
""".format(
    item.barcode,
    item.quantity,
    item.raw_prices,
    unit_price,
    tutar,
    maliyet,
    ecz_kar,
))


    return SaleItemFromScan(
        urun_id=item.barcode,
        urun_name=product.get("tr_name") or product.get("name"),
        miktar=item.quantity or 1,

        # 🔥 ADMIN-ONLY FIELDS
        birim_fiyat=unit_price,
        tutar=tutar,

        # mevcut finansal alanlar
        maliyet=maliyet,
        ecz_kar=ecz_kar,

        match_confidence=1.0,
    )
