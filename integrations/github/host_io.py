"""Host-owned bounded file, JSON, timestamp, and observed-status utilities.

Contract schemas, workflow planning, artifact semantics, and effect decisions
belong to the installed sfstack CLI. These helpers supply only local I/O and
aggregation of the GitHub host's own execution observations.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_FILE_BYTES = 16 * 1024 * 1024


def read_regular(path, maximum=MAX_FILE_BYTES):
    """Read bounded bytes without following a swapped final symlink or FIFO."""
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"Expected a regular file: {Path(path).name}")
        if info.st_size > maximum:
            raise ValueError(f"File exceeds {maximum} bytes: {Path(path).name}")
        raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise ValueError(f"File exceeds {maximum} bytes: {Path(path).name}")
        return raw


def strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid_constant(value):
        raise ValueError("Non-finite JSON number: " + value)

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def load_json(path, expected_sha256=None):
    raw = read_regular(path)
    if expected_sha256 is not None and hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError(f"Evidence digest mismatch: {Path(path).name}")
    return strict_json(raw.decode("utf-8"))


def contained_path(base, relative):
    if not relative or Path(relative).is_absolute() or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", relative):
        raise ValueError(f"Expected a relative local path: {relative}")
    base = Path(base).resolve()
    result = (base / relative).resolve()
    if not result.is_relative_to(base):
        raise ValueError(f"Path escapes its manifest directory: {relative}")
    return result


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise ValueError("Timestamps must include UTC (Z or +00:00).")
    return result


def now(value=None):
    return timestamp(value) if value else datetime.now(timezone.utc)


def report_status(statuses):
    """Aggregate observed host execution outcomes; this grants no authority."""
    return next(item for item in ("failed", "blocked", "inconclusive", "passed") if item in statuses)
