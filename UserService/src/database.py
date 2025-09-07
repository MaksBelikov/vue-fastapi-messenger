from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config import settings

async_engine = create_async_engine(
    url=settings.DATABASE_URL_asyncpg,
    echo=settings.DB_ENGINE_ECHO
)

Session = async_sessionmaker(async_engine)

class Base(DeclarativeBase): pass