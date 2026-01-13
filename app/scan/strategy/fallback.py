from typing import List, Dict, Any

from app.scan.strategy.base import ReportStrategy


class FallbackStrategy(ReportStrategy):
    name = "FALLBACK"

    def parse(
        self,
        lines: List[str],
        product_map: Dict[str, dict],
    ) -> Dict[str, Any]:

        print("🔴 Using FALLBACK strategy")

        return {
            "items": [],
        }
