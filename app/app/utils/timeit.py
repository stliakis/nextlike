import time
from app.utils.logging import log


class Timeit(object):
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        self.start = time.time()

    def __exit__(self, *args):
        log("info", f"{self.message}:took {(time.time() - self.start)*1000:.2f} millis")
