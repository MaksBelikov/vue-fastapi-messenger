import asyncio

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.ext.asyncio import AsyncSession
import uvicorn

import crud
from event_handlers import start_rabbitmq_consumer
from schemas import ChatResponse, ChatCreate, MessageResponse, MessageCreate, UserInDB
from dependencies import get_current_user, get_current_user_ws, get_db
from ws_manager import ws_manager
from ws_manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(start_rabbitmq_consumer())

    yield


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/{chat_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    chat_id: int,
    token: str
):
    try:
        user = await get_current_user_ws(token)
    except Exception as e:
        await websocket.close(code=1008, reason="Authentication failed")
        return

    await websocket.accept()
    
    await ws_manager.connect(user.id, websocket)
    await ws_manager.subscribe_to_chat(user.id, chat_id)
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.unsubscribe_from_chat(user.id, chat_id)
        await ws_manager.disconnect(user.id, websocket)


@app.post("/chats/", response_model=ChatResponse)
async def create_chat(
    chat: ChatCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.id not in chat.users_ids:
        chat.users_ids.append(current_user.id)
    
    return await crud.create_chat(db, chat)


@app.get("/chats/", response_model=list[ChatResponse])
async def get_user_chats(
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return await crud.get_user_chats(db, current_user.id)


@app.post("/messages/", response_model=MessageResponse)
async def send_message(
    request_message: MessageCreate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    message = await crud.create_message(db, request_message, current_user.id)
    
    if not message:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant of this chat"
        )
    
    ws_message = {
        "type": "new_message",
        "data": {
            "id": message.id,
            "chat_id": message.chat_id,
            "sender_id": message.sender_id,
            "content": message.content,
            "sent_at": message.sent_at.isoformat()
        }
    }
    await ws_manager.broadcast_to_chat(message.chat_id, ws_message)

    return message


@app.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
async def get_messages(
    chat_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    messages = await crud.get_chat_messages(db, chat_id, current_user.id, skip, limit)
    if messages is None:
        raise HTTPException(
            status_code=403,
            detail="You are not a participant of this chat"
        )
    return messages


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)