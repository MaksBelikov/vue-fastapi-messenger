from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from models import ChatOrm, ParticipantOrm, MessageOrm, UserOrm
from schemas import ChatResponse, ChatCreate, MessageResponse, MessageCreate

async def create_chat(db: AsyncSession, chat: ChatCreate) -> ChatResponse:
    db_chat = ChatOrm(
        is_group=chat.is_group,
        title=chat.title
    )
    db.add(db_chat)

    await db.flush()
    await db.refresh(db_chat, ["users"])

    users = (await db.scalars(select(UserOrm)
                                     .filter(UserOrm.id.in_(chat.users_ids)))).all()
    for user in users:
        db_chat.users.append(user)
    

    await db.refresh(db_chat)
    
    return ChatResponse.model_validate(db_chat)

async def get_user_chats(db: AsyncSession, user_id: int) -> list[ChatResponse]:
    result = await db.scalars(
        select(ChatOrm)
        .join(ParticipantOrm)
        .where(ParticipantOrm.user_id == user_id)
        .options(selectinload(ChatOrm.users))
    )
    return [ChatResponse.model_validate(chat) for chat in result] 

async def create_message(db: AsyncSession, message: MessageCreate, sender_id: int) -> MessageResponse | None:
    participant = await db.scalar(
        select(ParticipantOrm)
        .where(
            ParticipantOrm.chat_id == message.chat_id,
            ParticipantOrm.user_id == sender_id
        )
    )
    if not participant:
        return None
    
    db_message = MessageOrm(
        **message.model_dump(),
        sender_id=sender_id
    )
    db.add(db_message)

    await db.flush()
    await db.refresh(db_message)

    return MessageResponse.model_validate(db_message)

async def get_chat_messages(db: AsyncSession, chat_id: int, user_id: int, skip: int = 0, limit: int = 100) -> list[MessageResponse] | None:
    participant = await db.scalar(
        select(ParticipantOrm)
        .where(
            ParticipantOrm.chat_id == chat_id,
            ParticipantOrm.user_id == user_id
        )
    )
    if not participant:
        return None
    
    result = await db.scalars(
        select(MessageOrm)
        .where(MessageOrm.chat_id == chat_id)
        .order_by(MessageOrm.sent_at.desc())
        .offset(skip)
        .limit(limit)
        .options(selectinload(MessageOrm.sender))
    )
    return [MessageResponse.model_validate(message) for message in result]