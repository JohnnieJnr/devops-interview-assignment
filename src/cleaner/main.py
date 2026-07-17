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
from typing import Any

from cleaner.config import Config
from cleaner.keycloak_client import KeycloakClient, KeycloakError


MILLIS_PER_DAY = 24 * 60 * 60 * 1000


def main() -> int:
    try:
        config = Config.from_env()
        client = KeycloakClient(
            config.keycloak_url,
            config.realm,
            config.client_id,
            config.client_secret,
        )
        users = client.list_users()
        stale_users = find_stale_users(users, config, now_ms=int(time.time() * 1000))

        for candidate in stale_users:
            audit("candidate", candidate)
            if not config.dry_run:
                client.delete_user(candidate["id"])
                audit("deleted", candidate)

        summary = {
            "realm": config.realm,
            "dry_run": config.dry_run,
            "inactivity_days": config.inactivity_days,
            "users_seen": len(users),
            "stale_candidates": len(stale_users),
            "deleted": 0 if config.dry_run else len(stale_users),
        }
        print(json.dumps({"event": "summary", **summary}, sort_keys=True))
        return 0
    except (KeycloakError, ValueError) as exc:
        print(f"cleanup failed: {exc}", file=sys.stderr)
        return 1


def find_stale_users(
    users: list[dict[str, Any]],
    config: Config,
    now_ms: int,
) -> list[dict[str, Any]]:
    cutoff_ms = now_ms - (config.inactivity_days * MILLIS_PER_DAY)
    excluded = {username.lower() for username in config.exclusions}
    stale_users: list[dict[str, Any]] = []

    for user in users:
        username = str(user.get("username", ""))
        user_id = str(user.get("id", ""))

        if is_excluded(username, excluded):
            audit("skipped", {"id": user_id, "username": username, "reason": "excluded"})
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


def audit(event: str, payload: dict[str, Any]) -> None:
    print(json.dumps({"event": event, **payload}, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())
