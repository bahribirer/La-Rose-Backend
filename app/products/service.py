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
    res = []
    for p in products:
        # Prefer tr_name if available, else name
        best_name = p.get("tr_name") or p.get("name") or "Bilinmeyen Ürün"
        
        res.append({
            "id": p["id"],
            "name": best_name,
            "tr_name": best_name, 
            "volume": p.get("volume"),
            "category": p.get("category"),
            "psf_price": p.get("psf_price"),
            "esf_price": p.get("esf_price"),
            "wsf_price": p.get("wsf_price"),
            "price_eur": p.get("price_eur"),
            "price_51": p.get("price_51"),
            "cost": p.get("cost"),
            "profit": p.get("profit"),
            "markup": p.get("markup"),
            "margin": p.get("margin"),
            "gtin": p.get("gtin") or p["id"]
        })
    return res


    return {
        "total": total,
        "count": len(result),
        "items": result
    }
