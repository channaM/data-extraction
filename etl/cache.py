"""Redis cache layer: track ETL runs and cache record lookups."""
import json
import logging
from datetime import timedelta

import redis

from etl.config import Config

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None

TTL_RUN = int(timedelta(hours=24).total_seconds())
TTL_RECORD = int(timedelta(hours=1).total_seconds())


def get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            decode_responses=True,
        )
        _client.ping()
        logger.info("Redis connected at %s:%s", Config.REDIS_HOST, Config.REDIS_PORT)
    return _client


def cache_run_start(run_id: int, file_name: str, sheet_name: str) -> None:
    r = get_client()
    key = f"etl:run:{run_id}"
    r.hset(key, mapping={"file": file_name, "sheet": sheet_name, "status": "running"})
    r.expire(key, TTL_RUN)


def cache_run_finish(run_id: int, status: str, rows_loaded: int) -> None:
    r = get_client()
    key = f"etl:run:{run_id}"
    r.hset(key, mapping={"status": status, "rows_loaded": rows_loaded})
    r.expire(key, TTL_RUN)


def cache_record(external_id: str, record: dict) -> None:
    if not external_id:
        return
    r = get_client()
    key = f"etl:record:{external_id}"
    r.set(key, json.dumps(record, default=str), ex=TTL_RECORD)


def get_cached_record(external_id: str) -> dict | None:
    r = get_client()
    key = f"etl:record:{external_id}"
    raw = r.get(key)
    if raw:
        logger.debug("Cache hit for record '%s'.", external_id)
        return json.loads(raw)
    return None


def get_run_status(run_id: int) -> dict | None:
    r = get_client()
    key = f"etl:run:{run_id}"
    data = r.hgetall(key)
    return data or None
