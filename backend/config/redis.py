from redis.asyncio import from_url, Redis
from config.settings import settings

redis_client: Redis = None

async def connect():
    global redis_client
    redis_client = await from_url(settings.redis_url, decode_responses=True)

async def disconnect():
    if redis_client:
        await redis_client.aclose()
