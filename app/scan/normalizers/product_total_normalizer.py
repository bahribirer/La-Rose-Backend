from typing import Optional, Tuple, List
import itertools


def normalize_product_total_prices(
    floats: List[float],
    candidate_quantities: List[int],
) -> Tuple[
    Optional[float],  # unit_price
    Optional[float],  # maliyet
    Optional[float],  # ecz_kar
    Optional[float],  # tutar
    int,              # selected_quantity
]:
    """
    PRODUCT_TOTAL – sağlam semantik:
    1. maliyet + ecz_kar ≈ tutar
    2. quantity * unit_price ≈ tutar (veya tutar'ın kendisi unit_price ise qty=1)
    """
    
    # Varsayılan
    selected_qty = 1
    if candidate_quantities:
        # Default strategy: First integer (Sold Qty usually first, but we will verify)
        selected_qty = candidate_quantities[0]

    if not floats or len(floats) < 3:
        return None, None, None, None, selected_qty

    # 🔥 anlamsız küçük değerleri (KDV, oran vs) ayıkla
    candidates = [f for f in floats if f >= 0.01]

    if len(candidates) < 3:
        return None, None, None, None, selected_qty

    EPS = 0.5  # tolerans
    
    maliyet = None
    ecz_kar = None
    tutar = None

    # 1️⃣ KEŞİF: Finansal Toplamları Bul (a + b = c)
    # Genelde: Maliyet + Kar = Tutar
    best_triplet = None
    
    for a, b, c in itertools.permutations(candidates, 3):
        if abs((a + b) - c) < EPS:
            best_triplet = (a, b, c)
            # Genelde Maliyet > Kar (TR Eczane matematiği)
            maliyet = max(a, b)
            ecz_kar = min(a, b)
            tutar = c
            break

    # fallback (çok nadir, tutar=max kabul et)
    if tutar is None:
        tutar = max(candidates)
        maliyet = None
        ecz_kar = None

    # 2️⃣ QUANTITY SEÇİMİ (Smart Detection)
    # Tutar belli, şimdi candidate_quantities içinden hangisi Tutar'ı rasyonalize ediyor ona bakalım.
    # Kural: Tutar / Qty = Birim Fiyat (Bu Birim Fiyat listede var mı?)
    
    if tutar and candidate_quantities:
        for q in candidate_quantities:
            if q <= 0: continue
            
            calculated_unit_price = tutar / q
            
            # Bu hesaplanan fiyat, listedeki herhangi bir sayıya benziyor mu?
            # Örn: Tutar=1600, Q=1 -> Unit=1600. Listede 1600 var mı? Var. Match!
            # Örn: Tutar=1600, Q=8 -> Unit=200. Listede 200 var mı? Yok. Fail.
            
            match = False
            for f in floats:
                if abs(f - calculated_unit_price) < EPS:
                    match = True
                    break
            
            if match:
                selected_qty = q
                break
        
        # Eğer hiç match yoksa ve elimizde multiple candidates varsa
        # Ve eğer "First Integer Rule" ile "Stok" yiyorsak (örn. 8, 1)
        # Genelde satılan adet küçüktür (ama riskli).
        # Şimdilik: Match yoksa 'candidate_quantities[0]' (ilk tespit edilen) kullanmaya devam ediyoruz.
        # Yukardaki loop sadece "Daha iyi bir aday" varsa onu öne çıkarır.

    unit_price = None
    if tutar and selected_qty:
        unit_price = round(tutar / selected_qty, 2)

    return unit_price, maliyet, ecz_kar, tutar, selected_qty
