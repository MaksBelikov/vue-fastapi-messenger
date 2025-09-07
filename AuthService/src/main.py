from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext

from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm

from sqlalchemy.ext.asyncio import AsyncSession

import jwt
import uvicorn
from events import send_user_created_event
from models import UserOrm
from schemas import UserResponse, UserInDB, UserCreate, Token
from dependencies import get_user, get_current_user, get_db
from config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


async def authenticate_user(username: str, password: str) -> UserInDB | None:
    user = await get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.PRIVATE_KEY, algorithm=settings.ALGORITHM)


@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    if await get_user(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user_data.password)
    
    user_in_db = UserOrm(
        **user_data.model_dump(exclude={"password"}),
        hashed_password=hashed_password,
        disabled=False
    )
    
    db.add(user_in_db)

    await db.flush()
    await db.refresh(user_in_db)

    background_tasks.add_task(
        send_user_created_event,
        user_id=user_in_db.id,
        username=user_in_db.username
    )
    
    return user_in_db


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return current_user


@app.get("/protected")
async def protected_route(current_user: UserInDB = Depends(get_current_user)):
    return {
        "message": "Access granted",
        "username": current_user.username,
        "status": "active"
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)