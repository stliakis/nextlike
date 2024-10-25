import pickle
from pymemcache.client import base
from pymemcache.client.retrying import RetryingClient
from pymemcache.exceptions import MemcacheUnexpectedCloseError

from app.settings import get_settings

_client = None


def get_cache():
    global _client
    if _client:
        return _client

    host, port = get_settings().MEMCACHED_HOST.split(":")

    def pickle_serializer(key, value):
        if isinstance(value, str):
            return value.encode('utf-8'), 1
        return pickle.dumps(value), 2

    def pickle_deserializer(key, value, flags):
        if flags == 1:
            return value.decode('utf-8')
        elif flags == 2:
            return pickle.loads(value)
        raise Exception("Unknown flags {}".format(flags))

    _client = base.PooledClient((host, int(port)), serializer=pickle_serializer, deserializer=pickle_deserializer)

    _client = RetryingClient(
        _client,
        attempts=10,
        retry_delay=0.01,
        retry_for=[MemcacheUnexpectedCloseError]
    )

    return _client


def get_fake_cache():
    class FakeCache:
        def get(self, key):
            return None

        def set(self, key, value, time):
            pass

        def close(self):
            pass

    return FakeCache()


class SafeCache(object):
    def __init__(self, cache):
        self.cache = cache

    def set(self, *args, **kwargs):
        try:
            self.cache.set(*args, **kwargs)
        except Exception as e:
            print(f"Error setting cache: {e}")

    def get(self, *args, **kwargs):
        try:
            return self.cache.get(*args, **kwargs)
        except Exception as e:
            print(f"Error getting cache: {e}")
            return None


class Cache:
    def __init__(self, enabled=True):
        self.enabled = enabled

    def __enter__(self):
        if self.enabled:
            self.client = get_cache()
        else:
            self.client = get_fake_cache()
        return SafeCache(self.client)

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.client.close()
        return False
