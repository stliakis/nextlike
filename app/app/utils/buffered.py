class Buffered(object):
    def __init__(self, on_flush, size=10):
        self.items = []
        self.size = size
        self.on_flush = on_flush

    async def append(self, item):
        self.items.append(item)
        if len(self.items) > self.size:
            await self.flush()

    async def flush(self):
        if self.items:
            await self.on_flush(self.items)
            self.items = []
