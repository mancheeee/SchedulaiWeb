from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from typing import List

class ChatMessage(BaseModel):
    sender: str
    message: str
    session_id: Optional[str]
    timestamp: Optional[datetime] = datetime.utcnow()


class User(BaseModel):
    email: str
    name: Optional[str]
    timezone: Optional[str]


from typing import List

class EventData(BaseModel):
    title: str
    date: str
    start_range: Optional[str] = None
    end_range: Optional[str] = None
    duration: Optional[int] = None  
    participants: List[str]
