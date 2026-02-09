from pydantic import BaseModel
from typing import Optional, List


class Product(BaseModel):
    id: str
    name: str
    aliases: List[str] = []
    keywords: List[str] = []
    volume: Optional[str] = None
    category: Optional[str] = None
    gtin: Optional[str] = None
    esf_price: Optional[float] = None
    psf_price: Optional[float] = None
    wsf_price: Optional[float] = None
    price_eur: Optional[float] = None
    price_51: Optional[float] = None
    cost: Optional[float] = None
    markup: Optional[float] = None
    margin: Optional[float] = None
