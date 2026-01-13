# app/scan/models/parsed_sale_item.py
from typing import List, Optional

class ParsedSaleItem:
    def __init__(
        self,
        urun_id: str,
        urun_name: str,
        miktar: int,
        net_total: Optional[float],
        maliyet: Optional[float],
        ecz_kar: Optional[float],
        raw_prices: List[float],
        confidence: float,
    ):
        self.urun_id = urun_id
        self.urun_name = urun_name
        self.miktar = miktar

        # admin
        self.net_total = net_total
        self.maliyet = maliyet
        self.ecz_kar = ecz_kar

        # debug
        self.raw_prices = raw_prices
        self.confidence = confidence
