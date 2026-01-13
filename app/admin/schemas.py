from pydantic import BaseModel
from typing import List, Optional


class OverviewMetrics(BaseModel):
    total_reports: int
    total_revenue: float
    total_profit: float
    total_items: int


class TopUser(BaseModel):
    user_id: str
    name: str
    total_revenue: float
    total_profit: float
    total_items: int


class TopProduct(BaseModel):
    product_id: Optional[str]   # 🔥 BURASI DEĞİŞTİ
    product_name: str
    quantity: int
    total_profit: float
    total_cost: float


class AdminOverviewResponse(BaseModel):
    overview: OverviewMetrics
    top_users: List[TopUser]
    top_products: List[TopProduct]
