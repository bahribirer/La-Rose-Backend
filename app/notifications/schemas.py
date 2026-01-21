from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class NotificationResponse(BaseModel):
    id: str = Field(alias="_id")
    title: str
    body: str
    type: str = "info" # 'report_reminder', 'info', etc.
    is_read: bool = False
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
