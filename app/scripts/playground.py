from app.resources.cache import get_cache

for i in range(100):
    cache = get_cache()
    cache.set("test", {
        "asds": "21"
    })

    print(cache.get("test"))
