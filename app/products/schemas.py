from pydantic import BaseModel
from typing import Optional, List


class Product(BaseModel):
    id: str
    name: str
    aliases: List[str] = []
    keywords: List[str] = []
    volume: Optional[str] = None
    cost: Optional[float] = None
