from pydantic import BaseModel
from datetime import datetime

class CompetitionResponse(BaseModel):
    id: str
    year: int
    month: int
    starts_at: datetime
    ends_at: datetime

    status: str  
    # upcoming | active | completed | cancelled

from typing import Literal, Optional

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

