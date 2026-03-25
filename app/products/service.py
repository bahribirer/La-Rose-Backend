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
            "gtin": p.get("gtin") or p["id"],
            "image_url": p.get("image_url"),
            "description": p.get("description"),
            "name_tr": p.get("name_tr"),
            "slug": p.get("slug"),
            "web_price": p.get("web_price"),
            "featured_web": bool(p.get("featured_web")),
        })
    return res


_WEB_CATEGORY_MAP = {
    "YÜZ BAKIM": "yuz-bakimi",
    "VÜCUT BAKIM": "vucut-bakimi",
    "GÜNEŞ SERİSİ": "gunes-bakimi",
    "HİJYEN": "gunluk-hijyen",
    "Mon Petit LR": "bebek-bakimi",
    "DUDAK BAKIM": "makyaj-bakim",
    "MAKYAJ": "makyaj-bakim",
    "AKSESUAR": "aksesuar",
    "RUTİN": "rutinler",
}


async def load_products_website() -> List[Dict]:
    """
    Web sitesi için public loader — fiyat bilgisi yok, slug dahil
    """
    products = await load_products()
    res = []
    for p in products:
        raw_cat = p.get("category") or ""
        web_cat = _WEB_CATEGORY_MAP.get(raw_cat, raw_cat.lower().replace(" ", "-"))
        res.append({
            "id": p["id"],
            "barcode": p.get("gtin") or p["id"],
            "name": p.get("name") or "",
            "name_tr": p.get("name_tr") or p.get("tr_name") or p.get("name") or "",
            "subtitle": p.get("volume"),
            "slug": p.get("slug") or "",
            "category": web_cat,
            "details": p.get("description"),
            "image": p.get("image_url"),
            "featured_web": bool(p.get("featured_web")),
            "price": p.get("web_price"),
        })
    return res
