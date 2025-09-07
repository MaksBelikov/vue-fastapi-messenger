import datetime
from typing import Annotated

from sqlalchemy import String, ForeignKey, text, Index
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base

created_at = Annotated[datetime.datetime, mapped_column(server_default=text("TIMEZONE('utc', now())"))]

class ContactOrm(Base):
    __tablename__ = "user_contacts"
    
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), primary_key=True)
    contact_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), primary_key=True)
    created_at: Mapped[created_at]
    is_blocked: Mapped[bool] = mapped_column(default=False)


class UserProfileOrm(Base):
    __tablename__ = "user_profiles"
    __table_args__ = (
        Index('idx_user_profiles_username', 'username', postgresql_using='gin', postgresql_ops={'username': 'gin_trgm_ops'}),
    )
    
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    first_name: Mapped[str | None] = mapped_column(String(50))
    last_name: Mapped[str | None] = mapped_column(String(50))
    avatar_url: Mapped[str | None]
    about: Mapped[str | None] = mapped_column(String(200))
    last_seen: Mapped[datetime.datetime | None]
    created_at: Mapped[created_at]
    
    contacts: Mapped[list["UserProfileOrm"]] = relationship(secondary="user_contacts",
                                                        primaryjoin=(id == ContactOrm.user_id),
                                                        secondaryjoin=(id == ContactOrm.contact_id))
