"""
Redis cache service wrapper with graceful fallback.
Supports Upstash Redis when configured; otherwise becomes a no-op.
"""
import os
import json
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Try to import Upstash client
try:
    from upstash_redis import Redis  # type: ignore
    UPSTASH_AVAILABLE = True
except Exception:
    UPSTASH_AVAILABLE = False


class CacheService:
    def __init__(self):
        self.enabled = False
        self.client = None

        url = os.getenv("UPSTASH_REDIS_URL")
        token = os.getenv("UPSTASH_REDIS_TOKEN")

        if UPSTASH_AVAILABLE and url and token:
            try:
                self.client = Redis(url=url, token=token)
                self.enabled = True
                logger.info("✅ Upstash Redis cache enabled")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Upstash Redis: {e}")
        else:
            logger.info("ℹ️ Redis cache disabled (missing package or credentials)")

    def get_json(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        try:
            raw = self.client.get(key)
            if raw is None:
                return None
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            return json.loads(raw)
        except Exception as e:
            logger.debug(f"Cache get_json miss/error for {key}: {e}")
            return None

    def set_json(self, key: str, value: Any, ttl_seconds: int = 0) -> None:
        if not self.enabled:
            return
        try:
            payload = json.dumps(value, default=str)
            if ttl_seconds > 0:
                self.client.set(key, payload, ex=ttl_seconds)
            else:
                self.client.set(key, payload)
        except Exception as e:
            logger.debug(f"Cache set_json error for {key}: {e}")

    def delete(self, key: str) -> None:
        if not self.enabled:
            return
        try:
            # Upstash uses DEL
            self.client.delete(key)
        except Exception:
            pass


cache = CacheService()
