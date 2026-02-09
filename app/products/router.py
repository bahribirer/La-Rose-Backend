from fastapi import APIRouter, Query, Depends, HTTPException
from typing import Optional
from app.products.service import load_products_public
from app.admin.dependencies import admin_required
from app.core.database import db

router = APIRouter(
    prefix="/products",
    tags=["Products"]
)

@router.get("/")
async def list_products(
    q: Optional[str] = Query(None, description="Search by name"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    # 🔹 LIST gelir
    products = await load_products_public()

    # 🔍 search
    if q:
        q = q.lower()
        products = [
            p for p in products
            if q in p.get("name", "").lower()
        ]

    total = len(products)

    # 📄 pagination
    items = products[offset: offset + limit]

    return {
        "total": total,
        "count": len(items),
        "items": items
    }

@router.patch("/admin/{product_id}", dependencies=[Depends(admin_required)])
async def update_product_metadata(product_id: str, payload: dict):
    # Calculate price_51 and cost if price_eur is provided
    if "price_eur" in payload:
        try:
            eur = float(payload["price_eur"])
            payload["price_51"] = eur * 51
            payload["cost"] = payload["price_51"] * 1.20 # Cost with 20% tax
        except (ValueError, TypeError):
            pass

    res = await db.products.update_one(
        {"id": product_id},
        {"$set": payload}
    )
    
    if res.matched_count == 0:
        raise HTTPException(404, "Ürün bulunamadı")
        
    # Invalidate cache if exists
    from app.products.service import load_products
    await load_products(force_reload=True)
    
    return {"message": "Ürün güncellendi"}
