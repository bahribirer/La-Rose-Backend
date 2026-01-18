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

    # 🔥 STRUCTURAL PRIORITY (Full Semantic Mapping)
    
    # 1. Quantity Check
    candidates = item.quantity_candidates
    if item.exact_quantity_match:
        candidates = [item.exact_quantity_match] + [c for c in candidates if c != item.exact_quantity_match]

    # 2. Financials Check
    # If we have explicit semantic extraction, USE IT.
    
    sem_tutar = item.exact_total_match
    sem_price = item.exact_price_match
    sem_profit = item.exact_profit_match
    sem_cost = item.exact_cost_match
    sem_qty = item.exact_quantity_match or (candidates[0] if candidates else 1)
    
    print(f"🔍 DEBUG: Mapper Decision for {item.barcode}")
    print(f"   Candidates: {candidates} (Exact Match: {item.exact_quantity_match})")
    print(f"   Semantic Values -> Total: {sem_tutar}, Price: {sem_price}, Qty: {sem_qty}")

    # If we have robust structure data (Total + Qty are definitive)
    if sem_tutar and sem_qty:
        unit_price = sem_price or round(sem_tutar / sem_qty, 2)
        maliyet = sem_cost or 0.0 # Default to 0 for admin panel display
        ecz_kar = sem_profit or 0.0
        tutar = sem_tutar
        selected_qty = sem_qty
        
        print("\n✨ SEMANTIC MAPPING SUCCESS:")
        print(f"   Barcode: {item.barcode}")
        print(f"   Qty: {selected_qty}, Total: {tutar}, Profit: {ecz_kar}, Cost: {maliyet}")
    
    else:
        # Fallback to Smart Normalization if headers were ambiguous
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
