"""JSON file-based cache for LeetCode API responses.

Persistence guarantee
---------------------
Every ``cache.set()`` call writes a complete JSON file to disk *immediately*
(atomic temp-file rename on POSIX; direct write on Windows).  The in-memory
state is the file itself, so no data is ever lost when the process exits or is
killed with Ctrl-C.

Cache layout under  <save_path>/.cache/
    companies/<slug>.json   – fetch_company_favorite_meta + fetch_company_questions
    cards/<slug>.json       – fetch_card_chapters
    card_items/<id>.json    – fetch_card_item (per item id)
    questions/<slug>.json   – fetch_question

Each JSON file has the shape:
    {
        "slug": "...",
        "cached_at": "<ISO-8601 UTC timestamp>",
        "ttl_days": <int|null>,
        "data": <raw API payload>
    }

TTL invalidation
----------------
Pass ``ttl_days > 0`` to ``ApiCache`` to enable automatic expiry.  On the next
``get()`` call after the entry has aged past ``ttl_days`` the file is deleted
and ``None`` is returned so the caller re-fetches from the API.
When ``ttl_days=0`` (default) entries never expire.

Usage
-----
    from scraper.db import ApiCache

    cache = ApiCache(save_path, ttl_days=7)   # expire after 7 days

    # Company
    entry = cache.get("companies", slug)
    if entry:
        meta      = entry["meta"]
        questions = entry["questions"]
    else:
        meta = fetch_company_favorite_meta(headers, slug)
        questions = fetch_company_questions(...)
        cache.set("companies", slug, {"meta": meta, "questions": questions})

    # Card chapters
    entry = cache.get("cards", slug)
    chapters = entry["chapters"] if entry else None

    # Single card item
    entry = cache.get("card_items", str(item_id))

    # Question
    entry = cache.get("questions", slug)
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any

log = logging.getLogger(__name__)

# Subdirectories inside .cache/ for each data type
_BUCKETS = ("companies", "cards", "card_items", "questions", "playgrounds", "slides")


class ApiCache:
    """Persistent, optionally TTL-aware JSON file cache for LeetCode API data.

    Parameters
    ----------
    save_path:
        Root output directory (the same ``save_path`` from config).
    enabled:
        When False every ``get`` returns None and every ``set`` is a no-op.
        Controlled by the ``use_cache`` config option.
    ttl_days:
        Number of days before a cache entry is considered stale and evicted.
        ``0`` (default) means entries never expire.  Only active when
        ``enabled=True``.  Controlled by ``cache_ttl_days`` in config.
    """

    def __init__(self, save_path: str, enabled: bool = True, ttl_days: int = 0) -> None:
        self.enabled = enabled
        self.ttl_days = ttl_days
        self._root = os.path.join(save_path, ".cache")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _path(self, bucket: str, slug: str) -> str:
        bucket_dir = os.path.join(self._root, bucket)
        os.makedirs(bucket_dir, exist_ok=True)
        safe = slug.replace("/", "_").replace("\\", "_")
        return os.path.join(bucket_dir, f"{safe}.json")

    def _is_expired(self, cached_at_iso: str) -> bool:
        """Return True when TTL is enabled and the entry is older than ttl_days."""
        if self.ttl_days <= 0:
            return False
        try:
            cached_at = datetime.fromisoformat(cached_at_iso)
            if cached_at.tzinfo is None:
                cached_at = cached_at.replace(tzinfo=timezone.utc)
            age = datetime.now(timezone.utc) - cached_at
            return age > timedelta(days=self.ttl_days)
        except (ValueError, TypeError):
            return True  # if timestamp is unreadable, treat as expired

    def _atomic_write(self, path: str, entry: dict) -> None:
        """Write *entry* to *path* atomically so a mid-write exit leaves no corrupt file."""
        dir_name = os.path.dirname(path)
        # Write to a temp file in the same directory then rename (atomic on POSIX;
        # best-effort on Windows where rename replaces the target).
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(entry, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_path, path)   # atomic on POSIX; overwrites on Windows
        except OSError:
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            raise

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, bucket: str, slug: str) -> dict[str, Any] | None:
        """Return cached payload or None (on miss, disabled, or TTL expiry).

        When TTL is enabled and the entry has expired the file is deleted so
        the caller will re-fetch from the API on the next run.
        """
        if not self.enabled:
            return None
        path = self._path(bucket, slug)
        if not os.path.isfile(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as fh:
                entry = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Cache read failed for %s/%s: %s – treating as miss", bucket, slug, exc)
            return None

        # TTL check — only when ttl_days > 0
        if self._is_expired(entry.get("cached_at", "")):
            log.info("Cache EXPIRED [%s] %s (ttl=%dd) – evicting", bucket, slug, self.ttl_days)
            try:
                os.remove(path)
            except OSError:
                pass
            return None

        log.debug("Cache HIT  [%s] %s", bucket, slug)
        return entry.get("data")

    def set(self, bucket: str, slug: str, data: Any) -> None:
        """Write *data* to disk immediately so it survives process exit."""
        if not self.enabled:
            return
        path = self._path(bucket, slug)
        entry = {
            "slug": slug,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "ttl_days": self.ttl_days if self.ttl_days > 0 else None,
            "data": data,
        }
        try:
            self._atomic_write(path, entry)
            log.debug("Cache WRITE [%s] %s → %s", bucket, slug, path)
        except OSError as exc:
            log.warning("Cache write failed for %s/%s: %s", bucket, slug, exc)

    def invalidate(self, bucket: str, slug: str) -> bool:
        """Delete the cache entry for *slug* in *bucket*.  Returns True if deleted."""
        path = self._path(bucket, slug)
        if os.path.isfile(path):
            os.remove(path)
            log.info("Cache INVALIDATED [%s] %s", bucket, slug)
            return True
        return False

    def invalidate_all(self, bucket: str | None = None) -> int:
        """Delete all cached entries, optionally limited to one *bucket*.
        Returns the number of files deleted.
        """
        count = 0
        buckets = [bucket] if bucket else _BUCKETS
        for bkt in buckets:
            bkt_dir = os.path.join(self._root, bkt)
            if not os.path.isdir(bkt_dir):
                continue
            for fname in os.listdir(bkt_dir):
                if fname.endswith(".json"):
                    try:
                        os.remove(os.path.join(bkt_dir, fname))
                        count += 1
                    except OSError:
                        pass
        if count:
            log.info("Cache cleared: %d file(s) removed.", count)
        return count

    def stats(self) -> dict[str, int]:
        """Return {bucket: file_count} for every bucket."""
        result: dict[str, int] = {}
        for bkt in _BUCKETS:
            bkt_dir = os.path.join(self._root, bkt)
            if os.path.isdir(bkt_dir):
                result[bkt] = sum(1 for f in os.listdir(bkt_dir) if f.endswith(".json"))
            else:
                result[bkt] = 0
        return result
