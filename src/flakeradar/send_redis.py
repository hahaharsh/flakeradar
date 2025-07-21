from __future__ import annotations
import os, json
import redis

def publish_to_redis(project: str, summary: dict):
    url = os.getenv("REDIS_URL")
    if not url:
        return False
    r = redis.Redis.from_url(url)
    key = f"flakeradar:{project}:summary"
    r.set(key, json.dumps(summary))
    # also publish pub/sub for realtime dashboards
    r.publish("flakeradar.events", json.dumps({"project":project,"type":"summary"}))
    return True