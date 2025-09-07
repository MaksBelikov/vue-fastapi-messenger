from pydantic import BaseModel, EmailStr


class UserBase(BaseModel):
    username: str
    email: EmailStr | None


class UserCreate(UserBase):
    password: str


class UserResponse(UserBase):
    disabled: bool = False


class UserInDB(UserResponse):
    id: int
    hashed_password: str

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str