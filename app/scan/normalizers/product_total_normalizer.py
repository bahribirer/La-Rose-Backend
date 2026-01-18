from typing import Optional, Tuple, List
import itertools


def normalize_product_total_prices(
    floats: List[float],
    quantity: int,
) -> Tuple[
    Optional[float],  # unit_price
    Optional[float],  # maliyet
    Optional[float],  # ecz_kar
    Optional[float],  # tutar
]:
    """
    PRODUCT_TOTAL – sağlam semantik:
    maliyet + ecz_kar ≈ tutar
    """

    if not floats or len(floats) < 3:
        return None, None, None, None

    # 🔥 anlamsız küçük değerleri (KDV, oran vs) ayıkla
    # ARTIK < 10 filtrelemiyoruz, çünkü profit küçük olabilir (örn. 5.00 TL)
    candidates = [f for f in floats if f >= 0.01]

    if len(candidates) < 3:
        return None, None, None, None

    EPS = 0.5  # tolerans

    maliyet = None
    ecz_kar = None
    tutar = None

    # 🔑 TEMEL KURAL: a + b ≈ c
    for a, b, c in itertools.permutations(candidates, 3):
        if abs((a + b) - c) < EPS:
            # Genelde Maliyet > Kar (TR Eczane matematiği)
            maliyet = max(a, b)
            ecz_kar = min(a, b)
            tutar = c
            break

    # fallback (çok nadir)
    if tutar is None:
        tutar = max(candidates)
        maliyet = None
        ecz_kar = None

    unit_price = None
    if tutar and quantity:
        unit_price = round(tutar / quantity, 2)

    return unit_price, maliyet, ecz_kar, tutar
