from fastapi import APIRouter, Query, Depends, HTTPException
from app.products.service import load_products_public
from app.products.schemas import BulkUpdateItem
from typing import Optional, List
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

@router.post("/admin/bulk-update", dependencies=[Depends(admin_required)])
async def bulk_update_products(payload: List[BulkUpdateItem]):
    """
    Accepts a list of {id: string, ...updates} objects
    """
    from pymongo import UpdateOne
    
    operations = []
    for item in payload:
        p_id = item.id
        if not p_id: continue
        
        # Convert Pydantic model to dict, exclude unset fields and id
        updates = item.dict(exclude_unset=True, exclude={"id"})
        if not updates: continue
        
        operations.append(
            UpdateOne({"id": p_id}, {"$set": updates})
        )
    
    if operations:
        await db.products.bulk_write(operations)
        
    # Invalidate cache
    from app.products.service import load_products
    await load_products(force_reload=True)
    
    return {"message": f"{len(operations)} ürün güncellendi"}

@router.patch("/admin/{product_id}", dependencies=[Depends(admin_required)])
async def update_product_metadata(product_id: str, payload: dict):
    # Validations or other logic can go here if needed

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
