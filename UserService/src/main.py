import datetime
import asyncio
from fastapi import FastAPI, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import and_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn

from event_handlers import start_rabbitmq_consumer
from models import UserProfileOrm, ContactOrm
from schemas import UserProfileResponse, UserProfileWithContacts, ContactResponse, ContactCreate
from dependencies import get_current_user, get_current_user_ws, get_db
from redis_manager import init_redis, get_redis
from event_handlers import on_offline, on_online

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(start_rabbitmq_consumer())
    await init_redis()
    
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/profiles/me", response_model=UserProfileResponse)
async def get_profile(
    current_user: UserProfileResponse = Depends(get_current_user)
):
    return UserProfileResponse.model_validate(current_user)


@app.get("/profiles/search", response_model=list[UserProfileResponse])
async def search_users(
    query: str = Query(..., min_length=2),
    db: AsyncSession = Depends(get_db)
):
    results = (await db.execute(text("""
        SELECT * 
        FROM user_profiles
        WHERE username % :query
        ORDER BY similarity(username, :query) DESC
        LIMIT 20
    """), {"query": query})).all()
    
    return [UserProfileResponse.model_validate(profile) for profile in results] 


@app.post("/contacts/", response_model=ContactResponse)
async def add_contact(
    contact_data: ContactCreate,
    current_user: UserProfileResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Проверяем, что контакт существует
    contact_user = await db.get(UserProfileOrm, contact_data.contact_id)
    if not contact_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_contact = await db.scalar(select(ContactOrm)
                                       .filter(and_(ContactOrm.user_id == current_user.id, 
                                                    ContactOrm.contact_id == contact_data.contact_id)))
    
    if existing_contact:
        raise HTTPException(status_code=409, detail="Contact already exists")

    # Создаем связь контакта
    db_contact = ContactOrm(
        user_id=current_user.id,
        contact_id=contact_data.contact_id
    )
    db.add(db_contact)

    await db.commit()
    await db.refresh(db_contact)
    return ContactResponse.model_validate(db_contact)


@app.get("/contacts/", response_model=list[UserProfileResponse])
async def get_contacts(
    current_user: UserProfileWithContacts = Depends(get_current_user),
):
    return current_user.contacts


@app.websocket("/online")
async def user_online(
    websocket: WebSocket,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        user = await get_current_user_ws(token)
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await websocket.accept()

    redis = get_redis()
    pubsub = redis.pubsub() # type: ignore

    async def reader():
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=None)
            if message is not None:
                if message["type"] == "pmessage":
                    user_id = message["data"].decode().split(":")[-1]
                    if int(user_id) in [user.id for user in user.contacts]:
                        if message["channel"] == b"__keyevent@0__:expired":
                            await on_offline(websocket, user_id, datetime.datetime.now())
                        else:
                            await on_online(websocket, user_id, datetime.datetime.now())


    await pubsub.psubscribe("__keyevent@0__:expired")
    await pubsub.psubscribe("__keyevent@0__:set")
    
    asyncio.create_task(reader())

    try:
        while True:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            await get_redis().setex(f"user_status:{user.id}", 300, timestamp) # type: ignore
            await websocket.receive_text()
    except WebSocketDisconnect:
        await db.execute(update(UserProfileOrm)
                         .filter(UserProfileOrm.id == user.id)
                         .values(last_seen=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)))
        await redis.delete(f"user_status:{user.id}") # type: ignore


@app.get("/online/{user_id}")
async def get_user_online(user_id: int,
                          current_user: UserProfileResponse = Depends(get_current_user),
                          db: AsyncSession = Depends(get_db)):
    user_last_seen = await get_redis().get(f"user_status:{user_id}") # type: ignore
    if user_last_seen is not None:
        return {
            "status": "online",
            "last_seen": user_last_seen}
    
    user = await db.scalar(select(UserProfileOrm)
                    .filter(UserProfileOrm.id == user_id))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
            "status": "offline",
            "last_seen": user.last_seen}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)