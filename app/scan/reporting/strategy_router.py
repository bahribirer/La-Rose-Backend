from app.scan.reporting.report_types import ReportType

from app.scan.strategy.product_total import ProductTotalStrategy
from app.scan.strategy.product_summary import ProductSummaryStrategy
from app.scan.strategy.fallback import FallbackStrategy


_STRATEGY_REGISTRY = {
    ReportType.PRODUCT_TOTAL: ProductTotalStrategy,
    ReportType.PRODUCT_SUMMARY: ProductSummaryStrategy,
}


def get_strategy(report_type: ReportType):
    strategy_cls = _STRATEGY_REGISTRY.get(report_type)
    if strategy_cls:
        return strategy_cls()

    return FallbackStrategy()
