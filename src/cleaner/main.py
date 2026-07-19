"""Entry point.

Run with:
    python -m cleaner.main

Suggested flow:
    1. Load config from environment
    2. Build a Keycloak client
    3. List users, filter for stale ones (respect exclusions)
    4. If dry-run, log the candidates. Otherwise, delete them.
    5. Emit a summary (log line, metric, whatever fits your design)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from typing import Any

from cleaner.audit import audit, close_audit_log, init_audit_log
from cleaner.config import Config
from cleaner.keycloak_client import KeycloakClient, KeycloakError


MILLIS_PER_DAY = 24 * 60 * 60 * 1000


def main() -> int:
    config: Config | None = None
    try:
        config = Config.from_env()
        audit_log_file = init_audit_log(config.audit_log_file)
        client = KeycloakClient(
            config.keycloak_url,
            config.realm,
            config.client_id,
            config.client_secret,
        )
        audit(
            "run_started",
            {
                "audit_log_file": str(audit_log_file),
                "dry_run": config.dry_run,
                "inactivity_days": config.inactivity_days,
            },
            realm=config.realm,
        )
        users = client.list_users()
        stale_users = find_stale_users(
            users,
            config,
            now_ms=int(time.time() * 1000),
            realm=config.realm,
        )

        deleted_users: list[dict[str, Any]] = []
        for candidate in stale_users:
            audit("candidate", user_audit_record(candidate), realm=config.realm)
            if config.dry_run:
                audit(
                    "would_delete",
                    user_audit_record(candidate, action="dry_run"),
                    realm=config.realm,
                )
                continue

            try:
                client.delete_user(candidate["id"])
            except KeycloakError as exc:
                audit(
                    "delete_failed",
                    {**user_audit_record(candidate), "error": str(exc)},
                    realm=config.realm,
                )
                raise

            deleted_users.append(candidate)
            audit(
                "deleted",
                user_audit_record(
                    candidate,
                    action="user_deleted",
                    deleted_by=config.client_id,
                ),
                realm=config.realm,
            )

        summary: dict[str, Any] = {
            "dry_run": config.dry_run,
            "inactivity_days": config.inactivity_days,
            "users_seen": len(users),
            "stale_candidates": len(stale_users),
            "deleted": len(deleted_users),
        }
        if config.dry_run:
            summary["would_delete_users"] = [
                user_audit_record(user) for user in stale_users
            ]
        else:
            summary["deleted_users"] = [
                user_audit_record(user, deleted_by=config.client_id)
                for user in deleted_users
            ]

        audit("summary", summary, realm=config.realm)
        return 0
    except (KeycloakError, ValueError) as exc:
        print(f"cleanup failed: {exc}", file=sys.stderr)
        return 1
    finally:
        close_audit_log()


def find_stale_users(
    users: list[dict[str, Any]],
    config: Config,
    now_ms: int,
    *,
    realm: str,
) -> list[dict[str, Any]]:
    cutoff_ms = now_ms - (config.inactivity_days * MILLIS_PER_DAY)
    excluded = {username.lower() for username in config.exclusions}
    stale_users: list[dict[str, Any]] = []

    for user in users:
        username = str(user.get("username", ""))
        user_id = str(user.get("id", ""))

        if is_excluded(username, excluded):
            audit(
                "skipped",
                {"id": user_id, "username": username, "reason": "excluded"},
                realm=realm,
            )
            continue

        last_login_ms = extract_last_login_ms(user)
        if last_login_ms is None:
            audit(
                "skipped",
                {
                    "id": user_id,
                    "username": username,
                    "reason": "missing_or_invalid_lastLogin",
                },
                realm=realm,
            )
            continue

        if last_login_ms <= cutoff_ms:
            stale_users.append(
                {
                    "id": user_id,
                    "username": username,
                    "lastLogin": last_login_ms,
                    "inactiveDays": int((now_ms - last_login_ms) / MILLIS_PER_DAY),
                }
            )

    return stale_users


def is_excluded(username: str, exclusions: set[str]) -> bool:
    normalized = username.lower()
    return normalized in exclusions or normalized.startswith("service-account-")


def extract_last_login_ms(user: dict[str, Any]) -> int | None:
    attributes = user.get("attributes")
    if not isinstance(attributes, dict):
        return None

    raw_value = attributes.get("lastLogin")
    if isinstance(raw_value, list):
        raw_value = raw_value[0] if raw_value else None
    if raw_value is None:
        return None

    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None

    return parsed if parsed > 0 else None


def ms_to_iso(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()


def user_audit_record(user: dict[str, Any], **extra: Any) -> dict[str, Any]:
    last_login_ms = int(user["lastLogin"])
    record = {
        "id": user["id"],
        "username": user["username"],
        "inactiveDays": user["inactiveDays"],
        "lastLogin": last_login_ms,
        "lastLoginAt": ms_to_iso(last_login_ms),
    }
    record.update(extra)
    return record


if __name__ == "__main__":
    sys.exit(main())
