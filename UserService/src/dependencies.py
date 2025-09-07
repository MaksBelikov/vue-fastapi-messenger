from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import UserProfileOrm

from schemas import UserProfileWithContacts

from database import Session
from config import settings

import jwt

oauth2_scheme = HTTPBearer()

async def get_db() -> AsyncGenerator:
    async with Session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def get_user(username: str) -> UserProfileWithContacts | None:
    async with Session() as db:
        user = await db.scalar(select(UserProfileOrm)
                               .filter(UserProfileOrm.username == username)
                               .options(selectinload(UserProfileOrm.contacts)))
        if user:
            return UserProfileWithContacts.model_validate(user)
    return None


async def get_current_user(token= Depends(oauth2_scheme)) -> UserProfileWithContacts:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.PUBLIC_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        credentials_exception.detail = "Token has expired"
        raise credentials_exception
    except jwt.PyJWTError as a:
        print(a)
        raise credentials_exception
    
    user = await get_user(username)
    if not user:
        raise credentials_exception
    return user


async def get_current_user_ws(token: str) -> UserProfileWithContacts:
    try:
        payload = jwt.decode(token, settings.PUBLIC_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise Exception("Could not validate credentials")
    except (jwt.ExpiredSignatureError, HTTPException) as e:
        raise Exception("Token has expired")
    except (jwt.PyJWTError, HTTPException):
        raise Exception("Could not validate credentials")
    
    user = await get_user(username)
    if not user:
        raise Exception("Could not validate credentials")
    return user
