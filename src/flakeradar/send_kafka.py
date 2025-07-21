from __future__ import annotations
import os, json
from kafka import KafkaProducer

_producer_cache = None

def _get_producer():
    global _producer_cache
    if _producer_cache:
        return _producer_cache
    brokers = os.getenv("KAFKA_BROKERS")
    if not brokers:
        return None
    _producer_cache = KafkaProducer(
        bootstrap_servers=[b.strip() for b in brokers.split(",") if b.strip()],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    return _producer_cache

def send_kafka_event(project: str, run_summary: dict):
    prod = _get_producer()
    if not prod:
        return False
    topic = os.getenv("KAFKA_TOPIC", "flakeradar.local_runs")
    prod.send(topic, run_summary)
    prod.flush(timeout=5)
    return True