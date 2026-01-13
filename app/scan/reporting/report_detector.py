from app.scan.reporting.report_types import ReportType
import re

def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[\W_]+", " ", s)   # noktalama/_ temizle
    s = re.sub(r"\s+", " ", s).strip()
    return s

def detect_report_type(lines: list[str]) -> ReportType:
    text = _norm(" ".join(lines))

    rules = {
        ReportType.PRODUCT_TOTAL: ["ecz kar", "maliyet", "urun id", "stok"],
        ReportType.PRODUCT_SUMMARY: ["net satis", "kdv tutar", "genel toplam", "toplam satis"],
        ReportType.RECEIPT: ["fis", "kasa", "pos", "tutar", "odeme"],
    }

    scores = {t: 0 for t in rules}
    for t, keys in rules.items():
        for k in keys:
            if k in text:
                scores[t] += 1

    best_type = max(scores, key=scores.get)
    if scores[best_type] == 0:
        return ReportType.UNKNOWN

    # Tie-breaker (eşitlik)
    best_score = scores[best_type]
    tied = [t for t, s in scores.items() if s == best_score]
    if len(tied) > 1:
        # daha “spesifik” olanı tercih et
        priority = [ReportType.PRODUCT_TOTAL, ReportType.PRODUCT_SUMMARY, ReportType.RECEIPT]
        for p in priority:
            if p in tied:
                return p

    return best_type
