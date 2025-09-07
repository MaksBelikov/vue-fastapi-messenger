from redis.asyncio import Redis

from config import settings

redis = None

async def init_redis():
    global redis
    redis = await Redis(host=settings.REDIS_HOST, password=settings.REDIS_PASS)


def get_redis():
    return redis