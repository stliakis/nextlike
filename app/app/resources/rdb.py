import redis


def get_redis():
    return redis.Redis(host='localhost', port=6379, db=0)
