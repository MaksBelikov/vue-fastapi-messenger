from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class UserOrm(Base):
    __tablename__ = "users"
 
    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    username: Mapped[str]
    email: Mapped[str | None]
    hashed_password: Mapped[str]
    disabled: Mapped[bool | None]