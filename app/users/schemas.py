from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict


# ============================
# RESPONSE
# ============================

class UserProfileResponse(BaseModel):
    id: str
    email: Optional[str] = None
    full_name: Optional[str] = None

    phone_number: Optional[str] = None
    phone_verified: bool
    phone_verified_at: Optional[datetime]
    birth_date: Optional[str] = None
    position: Optional[str] = None
    avatar: Optional[str] = None
    onboarding_completed: Optional[bool] = None

    city: Optional[str] = None
    district: Optional[str] = None

    # ✅ FREE TEXT (ONBOARDING BEYANI)
    free_text_pharmacy_name: Optional[str] = None

    # 🔥 PHARMACY MATCH
    pharmacy_id: Optional[str] = None
    pharmacy_name: Optional[str] = None
    region: Optional[str] = None
    representative: Optional[str] = None


    model_config = {"from_attributes": True}


# ============================
# MATCH REQUEST
# ============================

class MatchPharmacyRequest(BaseModel):
    pharmacy_id: str


# ============================
# UPDATE REQUEST
# ============================

class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    birth_date: Optional[str] = None
    position: Optional[str] = None
    avatar: Optional[str] = None
    onboarding_completed: Optional[bool] = None
    city: Optional[str] = None
    district: Optional[str] = None

    # ✅ FREE TEXT (ONBOARDING BEYANI)
    free_text_pharmacy_name: Optional[str] = None

    model_config = {"extra": "forbid"}
