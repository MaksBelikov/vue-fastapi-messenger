from pydantic import BaseModel
from datetime import datetime

class UserProfileResponse(BaseModel):
    id: int
    username: str
    last_seen: datetime | None
    first_name: str | None = None
    last_name: str | None = None
    avatar_url: str | None = None
    about: str | None = None

    class Config:
        from_attributes = True

class UserProfileWithContacts(UserProfileResponse):
    contacts: list["UserProfileResponse"]

    class Config:
        from_attributes = True


class ContactCreate(BaseModel):
    contact_id: int

class ContactResponse(ContactCreate):
    user_id: int
    created_at: datetime
    is_blocked: bool
    
    class Config:
        from_attributes = True