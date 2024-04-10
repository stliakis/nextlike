import functools

CACHE_KEY_VERSION = "3"


class cached(object):
    def __init__(self, key, expire=60, keychain=None):
        self.key = key
        self.expire = expire
        self.keychain = keychain

    def __call__(self, fn):
        @functools.wraps(fn)
        def decorated(*args, **kwargs):
            # real_key = self.key(*args, **kwargs)

            # real_key = "%s:%s" % (real_key, CACHE_KEY_VERSION)

            # cache = get_cache()

            # rv = cache.get(real_key)
            # if rv:
            #     return rv.decode()
            # else:
            return fn(*args, **kwargs)
                # if rv is not None:
                #     cache.set(real_key, rv, self.expire)
                #
                #     if self.keychain:
                #         if callable(self.keychain):
                #             self.keychain(*args, **kwargs).add(real_key)
                #         else:
                #             self.keychain.add(real_key)
                #
                # return rv

        return decorated
