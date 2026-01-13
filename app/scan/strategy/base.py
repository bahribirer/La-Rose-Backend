from abc import ABC, abstractmethod
from typing import Dict, Any

class ReportStrategy(ABC):
    name: str = "base"

    @abstractmethod
    def parse(
        self,
        document,
        product_map: Dict[str, dict],
        table_hint: bool = False,
    ) -> Dict[str, Any]:
        raise NotImplementedError
