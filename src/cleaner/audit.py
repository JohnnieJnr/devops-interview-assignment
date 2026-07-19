"""Structured audit logging to stdout and a JSONL file."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

_audit_file: TextIO | None = None
_audit_log_path: Path | None = None


def init_audit_log(path: str) -> Path:
    """Open the audit log file for append and create parent directories."""
    global _audit_file, _audit_log_path

    audit_path = Path(path)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    _audit_log_path = audit_path
    _audit_file = audit_path.open("a", encoding="utf-8")
    return audit_path


def close_audit_log() -> None:
    global _audit_file
    if _audit_file is not None:
        _audit_file.close()
        _audit_file = None


def audit_log_path() -> Path | None:
    return _audit_log_path


def audit(event: str, payload: dict[str, Any], *, realm: str | None = None) -> None:
    record: dict[str, Any] = {
        "event": event,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    if realm is not None:
        record["realm"] = realm

    line = json.dumps(record, sort_keys=True)
    print(line, file=sys.stdout, flush=True)

    if _audit_file is not None:
        _audit_file.write(line + "\n")
        _audit_file.flush()
