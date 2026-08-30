from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker,create_async_engine
from typing import AsyncGenerator
from app.models.base import Base
from app.config import settings

'''
1. Create engine
2. Establish session_local
3. Init Db using asyc with engine().begin() ..; here we use engine to create new dbs
4. Now add get_db usig same with but now with session, here we use sessions
'''

engine = create_async_engine(
    url=settings.DATABASE_URL_ASYNC,
    echo=False,
    pool_size=50,
    max_overflow=100,
    pool_recycle=1800,
    pool_pre_ping=True
)

SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

async def init_db():
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

async def get_db():
    async with SessionLocal() as session:
        yield session