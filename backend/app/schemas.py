from datetime import datetime
from pydantic import BaseModel

class BookingRequest(BaseModel):
    intent: str
    date: datetime
    duration_minutes: int

class BookingSlot(BaseModel):
    start: datetime
    end: datetime
