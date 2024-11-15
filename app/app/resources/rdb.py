import redis.asyncio as redis

from app.settings import get_settings

_client = None


def get_redis():
    # global _client
    # if _client:
    #     return _client

    redis_connection_string = get_settings().REDIS_HOST
    redis_port = redis_connection_string.split(":")[-1]
    redis_host = redis_connection_string.split(":")[0]

    _client = redis.Redis(host=redis_host, port=int(redis_port), db=0)

    return _client
