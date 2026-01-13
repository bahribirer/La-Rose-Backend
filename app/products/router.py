from fastapi import APIRouter, Query
from typing import Optional
from app.products.service import load_products_public

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
