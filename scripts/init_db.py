import asyncio
from app.database.session import engine
from app.database.models import Base

async def init_db() -> None:
    print("Connection to PostgreSQL and creating tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Done! All tables created successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())