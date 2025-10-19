from __future__ import annotations

from typing import Any, Dict, List, Tuple, Optional

from ..db import q
from cachetools import TTLCache


async def latest_snapshot(tag_name: str | None) -> List[Dict[str, Any]]:
    sql = (
        "SELECT tag_name, value, ts "
        "FROM public.influx_latest "
        "WHERE (%s::text IS NULL OR tag_name = %s) "
        "ORDER BY tag_name "
        "LIMIT 1000"
    )
    params: Tuple[str | None, str | None] = (tag_name, tag_name)
    return await q(sql, params)


async def get_all_latest_values() -> List[Dict[str, Any]]:
    """모든 태그의 최신 값을 가져옴 (Dashboard용)"""
    return await latest_snapshot(None)


# Lightweight in-memory cache for latest values to avoid hammering DB from AI page
_latest_cache: TTLCache = TTLCache(maxsize=8, ttl=10)


async def get_latest_values_cached(tag_name: Optional[str] = None, ttl: int = 10) -> List[Dict[str, Any]]:
    """Return latest sensor values with a short TTL cache.

    - Caches per-tag and the all-tags (None) result separately
    - Default TTL 10s is enough for UI responsiveness while limiting DB load
    """
    global _latest_cache  # noqa: PLW0603
    
    # Adjust TTL dynamically if caller provides
    if _latest_cache.ttl != ttl:
        # cachetools doesn't support changing ttl in-place per entry;
        # recreate cache with same contents when ttl differs
        try:
            items = list(_latest_cache.items())
        except Exception:
            items = []
        _latest_cache = TTLCache(maxsize=8, ttl=ttl)
        for k, v in items:
            _latest_cache[k] = v

    key = ("latest", tag_name or "__all__")
    if key in _latest_cache:
        return _latest_cache[key]

    rows = await latest_snapshot(tag_name)
    _latest_cache[key] = rows
    return rows


