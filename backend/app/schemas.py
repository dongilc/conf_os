from datetime import date
from typing import Optional
from pydantic import BaseModel

class ConferenceCreate(BaseModel):
    year: int
    name: str
    theme: Optional[str] = None
    start_date: date
    end_date: date
    venue_name: Optional[str] = None
    venue_city: Optional[str] = None
    timezone: str = "Asia/Seoul"
    status: str = "planning"
