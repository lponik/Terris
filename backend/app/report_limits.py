"""In-memory report cache utilities."""

from __future__ import annotations

import copy
from collections import OrderedDict
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from fastapi import Request


_lock = RLock()
_report_cache: OrderedDict[str, tuple[datetime, dict[str, Any]]] = OrderedDict()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_client_ip(request: Request) -> str:
    """Get client IP, preferring x-forwarded-for when present."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        first = forwarded_for.split(",")[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _purge_expired_locked(ttl_seconds: int) -> None:
    now = _utcnow()
    expired_keys = [
        key
        for key, (created_at, _) in _report_cache.items()
        if (now - created_at).total_seconds() > ttl_seconds
    ]
    for key in expired_keys:
        _report_cache.pop(key, None)


def cache_get(cache_key: str, *, ttl_seconds: int) -> dict[str, Any] | None:
    """Get cached report if fresh."""
    with _lock:
        _purge_expired_locked(ttl_seconds)
        item = _report_cache.get(cache_key)
        if item is None:
            return None
        _report_cache.move_to_end(cache_key)
        _, value = item
        return copy.deepcopy(value)


def cache_set(cache_key: str, value: dict[str, Any], *, ttl_seconds: int, max_items: int) -> None:
    """Set cached report and enforce LRU + TTL constraints."""
    with _lock:
        _purge_expired_locked(ttl_seconds)
        _report_cache[cache_key] = (_utcnow(), copy.deepcopy(value))
        _report_cache.move_to_end(cache_key)
        while len(_report_cache) > max_items:
            _report_cache.popitem(last=False)
