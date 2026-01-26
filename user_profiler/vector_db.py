from .tools import config

def dump_user_intents(limit: int = 1000):
    points, next_offset = None, None
    while True:
        points, next_offset = config.qdrant.scroll("user_intents", limit=limit, offset=next_offset, with_payload=True, with_vectors=True)
        print(points)
        if next_offset is None: break

dump_user_intents()
