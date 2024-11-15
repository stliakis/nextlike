from app.resources.rdb import get_redis

from app.utils.logging import log


class RedisTemporalLock(object):
    def __init__(self, name, expire=3600 * 24 * 30):
        self.name = name
        self.expire = expire

    async def __aenter__(self):
        rdb = get_redis()
        locked = await rdb.get("rtl:%s" % self.name)
        rdb.setex("rtl:%s" % self.name, 1, self.expire)

        if locked:
            log("warning", "RedisTemporalLock(%s) is locked!" % self.name)
        else:
            log("warning", "RedisTemporalLock(%s) is unlocked!" % self.name)

        return not bool(locked)

    async def __aexit__(self, type, value, traceback):
        await get_redis().delete("rtl:%s" % self.name)
