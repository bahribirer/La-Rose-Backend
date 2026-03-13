from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional, List


# ================= PRIZE =================

class PrizeItem(BaseModel):
    place: int
    reward: str
    type: str = "gold"  # "gold" | "tl" | "other"


class UpdatePrizesBody(BaseModel):
    prizes: List[PrizeItem]


# ================= COMPETITION =================

class CompetitionResponse(BaseModel):
    id: str
    year: int
    month: int
    league: str = "-"
    starts_at: datetime
    ends_at: datetime
    status: str
    # upcoming | active | completed | cancelled
    prizes: Optional[List[PrizeItem]] = None


class UserCompetitionStatusResponse(BaseModel):
    status: Literal[
        "none",
        "registered",
        "accepted",
        "missed",
        "registration_open",
    ]

    can_register_next: Optional[bool] = None
    competition: Optional[CompetitionResponse] = None

