from typing import Dict


def score_product_total(f: Dict[str, bool]) -> float:
    score = 0.0
    if f["has_ecz_kar"]:
        score += 0.4
    if f["has_maliyet"]:
        score += 0.4
    if f["has_satis_tutari"]:
        score += 0.2
    return score


def score_product_summary(f: Dict[str, bool]) -> float:
    score = 0.0
    if f["has_net_satis"]:
        score += 0.4
    if f["has_kdv"]:
        score += 0.3
    if f["has_satis_tutari"]:
        score += 0.3
    return score


def score_receipt(f: Dict[str, bool]) -> float:
    score = 0.0
    if not f["has_ecz_kar"] and not f["has_net_satis"]:
        score += 0.5
    if f["has_bakiye"]:
        score += 0.5
    return score
