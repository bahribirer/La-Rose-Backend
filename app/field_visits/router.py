from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from bson import ObjectId
from app.core.database import db
from app.users.router import get_current_db_user

router = APIRouter(prefix="/field-visits", tags=["Field Visits"])


@router.post("")
async def create_field_visit(
    pharmacy_id: str,
    visit_date: str,  # YYYY-MM-DD
    visit_time: str,  # HH:MM
    notes: str = "",
    current_user=Depends(get_current_db_user),
):
    """Create a new field visit record."""
    if not ObjectId.is_valid(pharmacy_id):
        raise HTTPException(400, "Invalid pharmacy ID")

    # Verify pharmacy exists
    pharmacy = await db.pharmacies.find_one({"_id": ObjectId(pharmacy_id)})
    if not pharmacy:
        raise HTTPException(404, "Pharmacy not found")

    # Parse date and time
    try:
        visit_datetime = datetime.strptime(f"{visit_date} {visit_time}", "%Y-%m-%d %H:%M")
    except ValueError:
        raise HTTPException(400, "Invalid date or time format")

    # Create field visit record
    visit = {
        "user_id": current_user["_id"],
        "pharmacy_id": ObjectId(pharmacy_id),
        "pharmacy_name": pharmacy["pharmacy_name"],
        "pharmacy_district": pharmacy.get("district"),
        "pharmacy_region": pharmacy.get("region"),
        "visit_date": visit_date,
        "visit_time": visit_time,
        "visit_datetime": visit_datetime,
        "notes": notes,
        "created_at": datetime.utcnow(),
    }

    result = await db.field_visits.insert_one(visit)

    return {
        "status": "created",
        "id": str(result.inserted_id),
    }


@router.get("")
async def get_field_visits(
    year: int = Query(...),
    month: int = Query(...),
    current_user=Depends(get_current_db_user),
):
    """Get field visits for a specific month."""
    # Build date range
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    cursor = db.field_visits.find({
        "user_id": current_user["_id"],
        "visit_date": {"$gte": start_date, "$lt": end_date},
    }).sort("visit_datetime", 1)

    visits = []
    async for doc in cursor:
        visits.append({
            "id": str(doc["_id"]),
            "pharmacy_id": str(doc["pharmacy_id"]),
            "pharmacy_name": doc["pharmacy_name"],
            "pharmacy_district": doc.get("pharmacy_district"),
            "visit_date": doc["visit_date"],
            "visit_time": doc["visit_time"],
            "notes": doc.get("notes", ""),
        })

    return visits


@router.get("/by-date")
async def get_visits_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    current_user=Depends(get_current_db_user),
):
    """Get field visits for a specific date."""
    cursor = db.field_visits.find({
        "user_id": current_user["_id"],
        "visit_date": date,
    }).sort("visit_time", 1)

    visits = []
    async for doc in cursor:
        visits.append({
            "id": str(doc["_id"]),
            "pharmacy_id": str(doc["pharmacy_id"]),
            "pharmacy_name": doc["pharmacy_name"],
            "pharmacy_district": doc.get("pharmacy_district"),
            "visit_date": doc["visit_date"],
            "visit_time": doc["visit_time"],
            "notes": doc.get("notes", ""),
        })

    return visits


@router.delete("/{visit_id}")
async def delete_field_visit(
    visit_id: str,
    current_user=Depends(get_current_db_user),
):
    """Delete a field visit record."""
    if not ObjectId.is_valid(visit_id):
        raise HTTPException(400, "Invalid visit ID")

    result = await db.field_visits.delete_one({
        "_id": ObjectId(visit_id),
        "user_id": current_user["_id"],
    })

    if result.deleted_count == 0:
        raise HTTPException(404, "Visit not found")

    return {"status": "deleted"}
