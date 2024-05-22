import pickle
from pymemcache.client import base

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

    _client = base.Client((host, int(port)), serializer=pickle_serializer, deserializer=pickle_deserializer)

    return _client


class Cache:
    def __enter__(self):
        self.client = get_cache()
        return self.client

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.client.close()
        return False
