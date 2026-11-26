import asyncio
from sqlalchemy import text
import redis.asyncio as redis
from qdrant_client import QdrantClient
from app.core.config import get_settings
from app.database.session import engine

settings = get_settings()

async def test_all() -> None:
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        print("PostgreSQL connection! Result:",result.scalar())
    await engine.dispose()

    r = redis.from_url(settings.REDIS_URL)
    pong = await r.ping()
    print("Redis connected! Ping:", pong)
    await r.aclose()

    qdrant = QdrantClient(url=settings.QDRANT_URL)
    collections = qdrant.get_collections()
    print("Qdrant connected! Collections:",collections.collections)

if __name__ == "__main__":
    asyncio.run(test_all())

