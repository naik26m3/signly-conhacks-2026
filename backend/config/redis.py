from redis.asyncio import ConnectionPool, Redis
from config.settings import settings

class RedisClient:
    _pool: ConnectionPool = None
    _client: Redis = None

    @classmethod
    async def connect(cls):
        cls._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
        cls._client = Redis(connection_pool=cls._pool)

    @classmethod
    async def disconnect(cls):
        if cls._client:
            await cls._client.aclose()

    @classmethod
    def client(cls) -> Redis:
        return cls._client
