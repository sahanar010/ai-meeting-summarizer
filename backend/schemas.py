from typing import Optional
from pydantic import BaseModel


class ActionItem(BaseModel):
    task: str
    owner: Optional[str] = "Unassigned"
    due: Optional[str] = None


class MeetingResponse(BaseModel):
    id: str
    filename: str
    status: str
    error: Optional[str] = None
    transcript: Optional[str] = None
    summary: Optional[str] = None
    decisions: Optional[list[str]] = None
    action_items: Optional[list[ActionItem]] = None
    duration_seconds: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True
