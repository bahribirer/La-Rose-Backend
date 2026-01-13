from app.scan.reporting.report_types import ReportType
from app.sales.schemas import SaleItemFromScan


def normalize_confidence(
    items: list[SaleItemFromScan],
    report_type: ReportType,
    used_table_mode: bool = False,
) -> list[SaleItemFromScan]:

    type_multiplier = {
        ReportType.PRODUCT_TOTAL: 1.0,
        ReportType.PRODUCT_SUMMARY: 0.9,
        ReportType.RECEIPT: 0.8,
        ReportType.FALLBACK: 0.6,
    }

    base_mul = type_multiplier.get(report_type, 0.7)

    # 🔥 TABLE MODE BOOST
    if used_table_mode:
        base_mul *= 1.1

    for item in items:
        raw = item.match_confidence or 0.5
        final = raw * base_mul

        item.match_confidence = round(
            max(0.0, min(final, 1.0)), 3
        )

    return items
