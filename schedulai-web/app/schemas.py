from pydantic import BaseModel, Field, validator
from typing import List
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List, Optional
from typing import Optional
from pydantic import Field


class EventData(BaseModel):
    title: str
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    start_range: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    end_range: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    duration: int
    participants: List[str]

    @validator("date")
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Invalid date format. Expected YYYY-MM-DD")
        return v

    @validator("start_range", "end_range")
    def validate_time(cls, v):
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Invalid time format. Expected HH:MM")
        return v


# class FreeSlotRequest(BaseModel):
# date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
# start_range: str = Field(..., pattern=r"^\d{2}:\d{2}$")
# end_range: str = Field(..., pattern=r"^\d{2}:\d{2}$")
# duration: int


class FreeSlotRequest(BaseModel):
    date: str
    start_range: Optional[str] = Field(default="08:00")
    end_range: Optional[str] = Field(default="20:00")
    duration: Optional[int] = Field(default=60)


class DirectSlotBooking(BaseModel):
    title: str
    start: str  # ISO 8601 format
    end: str  # ISO 8601 format
    participants: List[str]
