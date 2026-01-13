from typing import List, Dict, Any
from app.scan.reporting.report_types import ReportType


def extract_features(lines: List[str]) -> Dict[str, bool]:
    joined = " ".join(lines).lower()

    return {
    "has_ecz_kar": "ecz.kar" in joined or "ecz kar" in joined,
    "has_maliyet": "maliyet" in joined,
    "has_net_satis": "net satış" in joined or "net satis" in joined,
    "has_kdv": "kdv" in joined,
    "has_satis_tutari": "satış tutarı" in joined or "satis tutari" in joined,
    "has_bakiye": "bakiye" in joined,
    "has_urun_bazinda": "ürün bazında satış raporu" in joined,

    # 👇 AZ ÖNCE EKLEDİKLERİN
    "has_sutun_basliklari": (
        "miktar" in joined
        and "net satış" in joined
        and "kdv" in joined
    ),
    "has_toplam_satiri": "toplam" in joined,

    # 👇 🔥 EKSİK OLANLAR (BUNLARI EKLE)
    "has_fis": "fiş" in joined or "fis" in joined,
    "has_kasa": "kasa" in joined,
}




def detect_report_type(lines: List[str]) -> ReportType:
    f = extract_features(lines)

    scores: Dict[ReportType, int] = {
        ReportType.PRODUCT_TOTAL: 0,
        ReportType.PRODUCT_SUMMARY: 0,
        ReportType.RECEIPT: 0,
        ReportType.FALLBACK: 0,
    }

    # 🔥 OVERRIDE (başlık netse tartışma yok)
    if f["has_urun_bazinda"]:
        return ReportType.PRODUCT_TOTAL

    # ---------- PRODUCT_TOTAL ----------
    if f["has_ecz_kar"]:
        scores[ReportType.PRODUCT_TOTAL] += 2
    if f["has_maliyet"]:
        scores[ReportType.PRODUCT_TOTAL] += 2
    if f["has_satis_tutari"]:
        scores[ReportType.PRODUCT_TOTAL] += 1

    # ---------- PRODUCT_SUMMARY ----------
    if f["has_net_satis"]:
        scores[ReportType.PRODUCT_SUMMARY] += 2
    if f["has_kdv"]:
        scores[ReportType.PRODUCT_SUMMARY] += 1
    if f["has_bakiye"]:
        scores[ReportType.PRODUCT_SUMMARY] += 1

    # ---------- RECEIPT ----------
    if f["has_fis"]:
        scores[ReportType.RECEIPT] += 2
    if f["has_kasa"]:
        scores[ReportType.RECEIPT] += 1

    # ---------- FALLBACK ----------
    scores[ReportType.FALLBACK] += 0

    # ---------- KARAR ----------
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]

    # Hiçbir şey tutmadıysa
    if best_score == 0:
        return ReportType.FALLBACK

    return best_type
