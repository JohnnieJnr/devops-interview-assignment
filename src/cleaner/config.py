"""Configuration loading.

Reads from environment variables. See .env.example for the expected shape.
"""

import os
from dataclasses import dataclass
from pathlib import Path


TRUE_VALUES = {"1", "true", "t", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "f", "no", "n", "off"}


@dataclass
class Config:
    keycloak_url: str
    realm: str
    client_id: str
    client_secret: str
    inactivity_days: int
    dry_run: bool
    exclusions: list[str]

    @classmethod
    def from_env(cls) -> "Config":
        values = _load_dotenv()
        values.update(os.environ)

        return cls(
            keycloak_url=_required(values, "KEYCLOAK_URL").rstrip("/"),
            realm=_required(values, "KEYCLOAK_REALM"),
            client_id=_required(values, "KEYCLOAK_CLIENT_ID"),
            client_secret=_required(values, "KEYCLOAK_CLIENT_SECRET"),
            inactivity_days=_positive_int(
                values.get("INACTIVITY_DAYS", "120"),
                "INACTIVITY_DAYS",
            ),
            dry_run=_bool(values.get("DRY_RUN", "true"), "DRY_RUN"),
            exclusions=_csv(values.get("EXCLUSIONS", "admin,break-glass")),
        )


def _load_dotenv(path: Path = Path(".env")) -> dict[str, str]:
    """Load a minimal KEY=value .env file without adding a runtime dependency."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _required(values: dict[str, str], name: str) -> str:
    value = values.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required")
    return value


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return parsed


def _bool(value: str, name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
