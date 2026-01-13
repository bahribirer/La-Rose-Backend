from app.core.database import db
from typing import List, Dict, Optional

# 🧠 in-memory cache
_PRODUCT_CACHE: Optional[List[Dict]] = None


async def load_products(force_reload: bool = False) -> List[Dict]:
    """
    Internal product loader (matcher, scan)
    """
    global _PRODUCT_CACHE

    if _PRODUCT_CACHE is not None and not force_reload:
        return _PRODUCT_CACHE

    cursor = db.products.find({}, {"_id": 0})
    products = await cursor.to_list(length=None)

    _PRODUCT_CACHE = products
    return products

async def load_products_public() -> List[Dict]:
    """
    Public API safe loader (NO pagination here)
    """
    products = await load_products()

    # 🔒 client-safe projection
    return [
        {
            "id": p["id"],
            "name": p["name"],
            "volume": p.get("volume")
        }
        for p in products
    ]


    return {
        "total": total,
        "count": len(result),
        "items": result
    }
