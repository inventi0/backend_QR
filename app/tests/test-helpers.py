# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# from sqlalchemy.orm import sessionmaker
#
# # Create async engine
# SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://user:password@localhost/dbname"  # Replace with your actual database URL
# engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)
#
# # Create async sessionmaker
# AsyncSessionLocal = sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
# )
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.orm import sessionmaker
# from app.models.models import Base
# from database.py import AsyncSessionLocal
#
# # Test helper to create a new session
# async def get_db() -> AsyncSession:
#     async with AsyncSessionLocal() as session:
#         yield session
#
# # Optionally, you can create a fixture for pytest like this:
# import pytest
# from sqlalchemy.ext.asyncio import AsyncSession
#
# @pytest.fixture
# async def db_session():
#     async with AsyncSessionLocal() as session:
#         # Set up the database for the test
#         yield session
#         # Optionally, you can clean up here
