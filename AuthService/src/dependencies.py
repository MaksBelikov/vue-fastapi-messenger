import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from sqlalchemy import select

from models import UserOrm
from schemas import UserInDB
from database import Session
from config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_db():
    async with Session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_user(username: str) -> UserInDB | None:
    async with Session() as db:
        user = await db.scalar(select(UserOrm).filter(UserOrm.username == username))
        if user:
            return UserInDB.model_validate(user)
    return None


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.PUBLIC_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        credentials_exception.detail = "Token has expired"
        raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = await get_user(username)
    if not user:
        raise credentials_exception
    return user
