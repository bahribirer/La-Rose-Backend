from app.sales.schemas import SaleItemFromScan
from app.scan.normalizers.product_total_normalizer import (
    normalize_product_total_prices,
)


def table_item_to_sale_item(item, product_map):
    print(f"🏁 ENTERING MAPPER for {item.barcode}...")
    if not item.barcode:
        return None
        
    # Robust cleanup: ensure strictly digits-only string for lookup
    clean_barcode = "".join(c for c in str(item.barcode) if c.isdigit())
    
    product = product_map.get(clean_barcode)
    
    # Check original if clean failed (fallback)
    if not product:
        product = product_map.get(item.barcode)

    if not product:
        # Debugging: Why is it failing?
        print(f"⚠️ MAPPER FAIL: Barcode '{clean_barcode}' (Orig: '{item.barcode}') not found in {len(product_map)} keys.")
        # Try finding by name fuzzy match? (Optional optimization later)
        return None
    else:
        # print(f"✅ MAPPER SUCCESS: Found {product.get('name')} for {clean_barcode}")
        pass

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

    # If we have robust structure data (Total + Qty OR Price + Qty)
    if (sem_tutar and sem_qty) or (sem_price and sem_qty):
        
        selected_qty = sem_qty
        
        # Case A: We have Total & Qty (Calculate Unit Price)
        if sem_tutar:
            tutar = sem_tutar
            if sem_price:
                unit_price = sem_price
            else:
                # User Request (Step 3240): Use Gross Line Total (Net + Tax = 1224.0) as 'Birim Fiyat'.
                # "1224 birim fiyat olarak yazcak çünkü 2 yle çarpmış zaten"
                tax_val = getattr(item, 'tax_amount', 0.0) or 0.0
                unit_price = tutar + tax_val
            
        # Case B: We have Unit Price & Qty (Calculate Total)
        elif sem_price:
            unit_price = sem_price
            gross_calc = unit_price * selected_qty
            discount_val = getattr(item, 'discount_amount', 0.0) or 0.0
            tutar = round(gross_calc - discount_val, 2)

        maliyet = sem_cost or 0.0 
        ecz_kar = sem_profit or 0.0
        
        print("\n✨ SEMANTIC MAPPING SUCCESS:")
        print(f"   Barcode: {item.barcode}")
        print(f"   Qty: {selected_qty}, Unit Price: {unit_price}, Total: {tutar}")
    
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


    # Discount / Tax / Gross
    discount = item.discount_amount or 0.0
    tax = item.tax_amount or 0.0
    gross_total = item.gross_total or (round(unit_price * selected_qty, 2) if unit_price and selected_qty else 0.0)

    return SaleItemFromScan(
        urun_id=item.barcode,
        urun_name=product.get("tr_name") or product.get("name"),
        miktar=selected_qty,

        # 🔥 ADMIN-ONLY FIELDS
        birim_fiyat=unit_price,
        tutar=tutar,
        
        # Extended Financials
        discount=discount,
        tax=tax,
        gross_total=gross_total,

        # mevcut finansal alanlar
        maliyet=maliyet,
        ecz_kar=ecz_kar,
        
        stok_miktari=item.exact_stock_match,

        match_confidence=1.0,
    )
