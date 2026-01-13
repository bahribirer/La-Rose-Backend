from pydantic import BaseModel
from typing import Optional

# ============================================================
# PROFILE UPDATE SCHEMA
# ============================================================

class ProfileUpdateRequest(BaseModel):
    # USERS
    full_name: Optional[str] = None

    # USER_PROFILES
    phone_number: Optional[str] = None
    birth_date: Optional[str] = None  # YYYY-MM-DD
    pharmacy_name: Optional[str] = None
    position: Optional[str] = None
    avatar: Optional[str] = None

    # ONBOARDING
    onboarding_completed: Optional[bool] = None

    

    class Config:
        extra = "forbid"
