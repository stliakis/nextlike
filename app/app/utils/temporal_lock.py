from app.resources.redis import get_redis


class RedisTemporalLock(object):
    def __init__(self, name, expire=3600 * 24 * 30):
        self.name = name
        self.expire = expire

    def __enter__(self):
        rdb = get_redis()
        locked = rdb.get("rtl:%s" % self.name)
        rdb.setex("rtl:%s" % self.name, 1, self.expire)

        # if locked:
        #     log("warning", "RedisTemporalLock(%s) is locked!" % self.name)
        # else:
        #     log("warning", "RedisTemporalLock(%s) is unlocked!" % self.name)

        return not bool(locked)

    def __exit__(self, type, value, traceback):
        get_redis().delete("rtl:%s" % self.name)
