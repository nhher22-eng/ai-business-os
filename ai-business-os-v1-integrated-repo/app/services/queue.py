import json
import redis
from app.core.config import settings

QUEUE_KEY = "aios:run:queue"

def client():
    return redis.Redis.from_url(settings.redis_url, decode_responses=True)

def enqueue_run(run_id: str):
    client().rpush(QUEUE_KEY, json.dumps({"run_id": run_id}))

def dequeue_run(timeout: int = 2):
    item = client().blpop(QUEUE_KEY, timeout=timeout)
    if not item:
        return None
    return json.loads(item[1])

def queue_depth() -> int:
    return int(client().llen(QUEUE_KEY))
