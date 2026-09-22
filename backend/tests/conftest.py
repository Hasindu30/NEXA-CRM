import asyncio
import os
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from alembic.config import Config
from alembic import command
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

# Safety Check
from app.core.config import settings

if not settings.test_database_url or not settings.test_database_url.endswith("crm_test"):
    raise RuntimeError("DANGER: TEST_DATABASE_URL must be configured and end with 'crm_test'.")

# OVERRIDE the application database_url with the test one for Alembic
settings.database_url = settings.test_database_url

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    import subprocess
    
    # Run migrations in a subprocess to avoid asyncpg loop-caching bugs across asyncio.run()
    import sys
    subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "base"], 
        check=True, 
        env={**os.environ, "DATABASE_URL": settings.test_database_url}
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], 
        check=True, 
        env={**os.environ, "DATABASE_URL": settings.test_database_url}
    )
    
    yield

@pytest_asyncio.fixture(scope="function")
async def db_engine():
    # Create engine inside the function loop
    engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    test_async_session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with db_engine.connect() as conn:
        trans = await conn.begin()
        async_session = test_async_session_maker(
            bind=conn,
            join_transaction_mode="create_savepoint"
        )
        yield async_session
        await async_session.close()
        await trans.rollback()
