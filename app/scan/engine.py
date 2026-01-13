from typing import Any, Dict
from app.scan.detector import detect_report_type, extract_features
from app.scan.ocr.line_extractor import extract_lines
from app.scan.reporting.strategy_router import get_strategy
from app.scan.utils.engine_confidence import normalize_confidence


def run_engine(
    document,
    product_map: Dict[str, dict],
) -> Dict[str, Any]:

    lines = extract_lines(document)
    features = extract_features(lines)
    report_type = detect_report_type(lines)

    print(f"\n🧠 REPORT TYPE DETECTED: {report_type}\n")

    strategy = get_strategy(report_type)

    table_hint = (
        features.get("has_sutun_basliklari")
        or features.get("has_urun_bazinda")
    )

    result = strategy.parse(
        document=document,
        product_map=product_map,
        table_hint=bool(table_hint),
    )
    used_table_mode = bool(
        result.get("_meta", {}).get("used_table")
    )


    # 🔥 CONFIDENCE NORMALIZATION (henüz boost yok)
    items = result.get("items", [])
    normalize_confidence(
    items,
    report_type,
    used_table_mode=used_table_mode,
)


    return {"items": items}
