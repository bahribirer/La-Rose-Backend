from typing import List, Optional, Tuple
import itertools


def infer_price_semantics(
    floats: List[float],
    quantity: int,
) -> Tuple[
    Optional[float],  # unit_price
    Optional[float],  # maliyet
    Optional[float],  # ecz_kar
    Optional[float],  # tutar
]:
    """
    Bu rapor tipi için kural:
    maliyet + ecz_kar ≈ tutar
    """

    if len(floats) < 3:
        return None, None, None, None

    # tolerans
    EPS = 0.5

    maliyet = ecz_kar = tutar = None

    # 1️⃣ Üçlü kombinasyonlarda a + b ≈ c ara
    for a, b, c in itertools.permutations(floats, 3):
        if abs((a + b) - c) < EPS:
            maliyet = a
            ecz_kar = b
            tutar = c
            break

    if tutar is None:
        # fallback (çok nadir)
        return None, None, None, None

    # 2️⃣ Birim fiyat
    unit_price = None
    if quantity > 0:
        unit_price = round(tutar / quantity, 2)

    return unit_price, maliyet, ecz_kar, tutar
