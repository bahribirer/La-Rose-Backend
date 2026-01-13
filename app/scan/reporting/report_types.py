from enum import Enum

class ReportType(str, Enum):
    PRODUCT_TOTAL = "PRODUCT_TOTAL"
    PRODUCT_SUMMARY = "PRODUCT_SUMMARY"
    RECEIPT = "RECEIPT"
    FALLBACK = "FALLBACK"   # 👈 EKLE
