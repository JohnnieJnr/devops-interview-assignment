"""Configuration loading.

Reads from environment variables. See .env.example for the expected shape.
"""

import os
from dataclasses import dataclass


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
        # TODO: implement
        raise NotImplementedError("Load config from environment variables.")
