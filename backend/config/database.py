from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config.settings import settings

class Base(DeclarativeBase):
    pass

class Database:
    engine = create_async_engine(
        settings.database_url,
        pool_size=10,    
        max_overflow=0,
        pool_timeout=30,   
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=False,
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)

    @classmethod
    async def connect(cls):
        async with cls.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def disconnect(cls):
        await cls.engine.dispose()

    @classmethod
    async def get_session(cls) -> AsyncSession:
        async with cls.Session() as session:
            yield session
