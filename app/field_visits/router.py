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
        "confirmed": False,
        "confirmed_at": None,
        "evaluation": None,
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
        visits.append(_serialize_visit(doc))

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
        visits.append(_serialize_visit(doc))

    return visits


@router.put("/{visit_id}/confirm")
async def confirm_field_visit(
    visit_id: str,
    current_user=Depends(get_current_db_user),
):
    """Mark a field visit as confirmed (gidildi)."""
    if not ObjectId.is_valid(visit_id):
        raise HTTPException(400, "Invalid visit ID")

    result = await db.field_visits.update_one(
        {"_id": ObjectId(visit_id), "user_id": current_user["_id"]},
        {"$set": {
            "confirmed": True,
            "confirmed_at": datetime.utcnow(),
        }},
    )

    if result.matched_count == 0:
        raise HTTPException(404, "Visit not found")

    return {"status": "confirmed"}


@router.put("/{visit_id}/evaluate")
async def evaluate_field_visit(
    visit_id: str,
    duration_hours: float = Query(..., description="Kaç saat kalındı"),
    transport_type: str = Query(..., description="taksi / kendi_araci / toplu_tasima / yuruyus"),
    taxi_cost: float = Query(0, description="Taksi ücreti (TL)"),
    pharmacist_rating: int = Query(..., ge=1, le=5, description="Eczacı tutumu 1-5"),
    evaluation_notes: str = Query("", description="Ek notlar"),
    current_user=Depends(get_current_db_user),
):
    """Evaluate a confirmed field visit."""
    if not ObjectId.is_valid(visit_id):
        raise HTTPException(400, "Invalid visit ID")

    # Verify visit exists, is confirmed, and belongs to user
    visit = await db.field_visits.find_one({
        "_id": ObjectId(visit_id),
        "user_id": current_user["_id"],
    })

    if not visit:
        raise HTTPException(404, "Visit not found")

    if not visit.get("confirmed"):
        raise HTTPException(400, "Visit must be confirmed first")

    evaluation = {
        "duration_hours": duration_hours,
        "transport_type": transport_type,
        "taxi_cost": taxi_cost if transport_type == "taksi" else 0,
        "pharmacist_rating": pharmacist_rating,
        "evaluation_notes": evaluation_notes,
        "evaluated_at": datetime.utcnow(),
    }

    await db.field_visits.update_one(
        {"_id": ObjectId(visit_id)},
        {"$set": {"evaluation": evaluation}},
    )

    return {"status": "evaluated"}


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


def _serialize_visit(doc):
    """Serialize a visit document for API response."""
    result = {
        "id": str(doc["_id"]),
        "pharmacy_id": str(doc["pharmacy_id"]),
        "pharmacy_name": doc["pharmacy_name"],
        "pharmacy_district": doc.get("pharmacy_district"),
        "visit_date": doc["visit_date"],
        "visit_time": doc["visit_time"],
        "notes": doc.get("notes", ""),
        "confirmed": doc.get("confirmed", False),
        "confirmed_at": doc.get("confirmed_at"),
    }

    evaluation = doc.get("evaluation")
    if evaluation:
        result["evaluation"] = {
            "duration_hours": evaluation["duration_hours"],
            "transport_type": evaluation["transport_type"],
            "taxi_cost": evaluation.get("taxi_cost", 0),
            "pharmacist_rating": evaluation["pharmacist_rating"],
            "evaluation_notes": evaluation.get("evaluation_notes", ""),
        }
    else:
        result["evaluation"] = None

    return result
