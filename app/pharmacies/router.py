from fastapi import APIRouter, Query
from app.core.database import db
from app.pharmacies.utils import normalize_text

router = APIRouter(prefix="/pharmacies", tags=["Pharmacies"])


@router.get("/search")
async def search_pharmacies(
    q: str = Query(..., min_length=2),
    limit: int = 10,
):
    normalized_q = normalize_text(q)

    cursor = db.pharmacies.find(
        {
            "normalized_name": {
                "$regex": f".*{normalized_q}.*",
                "$options": "i",
            }
        },
        {
            "_id": 1,
            "pharmacy_name": 1,
            "district": 1,
            "region": 1,
            "representative": 1,
        },
    ).limit(limit)

    results = []
    async for doc in cursor:
        results.append(
            {
                "id": str(doc["_id"]),
                "pharmacy_name": doc["pharmacy_name"],
                "district": doc.get("district"),
                "region": doc.get("region"),
                "representative": doc.get("representative"),
            }
        )

    return results
