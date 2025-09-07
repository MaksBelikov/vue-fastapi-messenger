import datetime

from typing import Annotated

from sqlalchemy import String, ForeignKey, text
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base


intpk = Annotated[int, mapped_column(primary_key=True, index=True)]
created_at = Annotated[datetime.datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]
updated_at = Annotated[datetime.datetime, mapped_column(
        server_default=text("TIMEZONE('utc', now())"),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))] 


class ChatOrm(Base):
    __tablename__ = "chats"
    
    id: Mapped[intpk]
    is_group: Mapped[bool] = mapped_column(default=False)
    title: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[created_at]
    
    messages: Mapped[list["MessageOrm"]] = relationship(back_populates="chat")
    users: Mapped[list["UserOrm"]] = relationship(back_populates="chats", secondary="participants")


class ParticipantOrm(Base):
    __tablename__ = "participants"
    
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[created_at]


class MessageOrm(Base):
    __tablename__ = "messages"
    
    id: Mapped[intpk]
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(nullable=False)
    sent_at: Mapped[created_at]
    edited_at: Mapped[updated_at]
    edited: Mapped[bool] = mapped_column(default=False)
    
    chat: Mapped["ChatOrm"] = relationship(back_populates="messages")
    sender: Mapped["UserOrm"] = relationship()


class UserOrm(Base):
    __tablename__ = "users"
 
    id: Mapped[intpk]
    username: Mapped[str]

    chats: Mapped[list["ChatOrm"]] = relationship(back_populates="users", secondary="participants")