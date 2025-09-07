from pydantic import BaseModel, Field
from datetime import datetime
from typing import List


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    chat_id: int


class MessageResponse(MessageCreate):
    id: int
    sender_id: int
    sent_at: datetime
    edited: bool
    
    class Config:
        from_attributes = True


class ChatBase(BaseModel):
    is_group: bool = False
    title: str | None = None


class ChatCreate(ChatBase):
    users_ids: List[int]


class ChatResponse(ChatBase):
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserInDB(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True