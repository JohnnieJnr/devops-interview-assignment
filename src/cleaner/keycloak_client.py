"""Keycloak Admin API client.

Suggested shape:
    - get_token()          - fetch an access token via client_credentials
    - list_users()         - paginate through the realm's users
    - delete_user(user_id) - delete (or disable, if you prefer soft delete)

You can use `python-keycloak`, `requests`, `httpx`, or roll your own.
No requirement — pick whatever fits your approach.
"""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


class KeycloakError(RuntimeError):
    """Raised when Keycloak returns an unexpected response."""


class KeycloakClient:
    def __init__(
        self,
        base_url: str,
        realm: str,
        client_id: str,
        client_secret: str,
        page_size: int = 100,
        timeout_seconds: int = 15,
    ):
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.page_size = page_size
        self.timeout_seconds = timeout_seconds
        self._token: str | None = None
        self._realm_path = quote(realm, safe="")

    def get_token(self) -> str:
        if self._token:
            return self._token

        token_url = f"{self.base_url}/realms/{self._realm_path}/protocol/openid-connect/token"
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode()
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = self._request("POST", token_url, body=body, headers=headers)
        token = response.get("access_token")
        if not isinstance(token, str) or not token:
            raise KeycloakError("Token response did not include access_token")

        self._token = token
        return token

    def list_users(self) -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        first = 0

        while True:
            params = urlencode(
                {
                    "first": first,
                    "max": self.page_size,
                    "briefRepresentation": "false",
                }
            )
            url = f"{self.base_url}/admin/realms/{self._realm_path}/users?{params}"
            page = self._request("GET", url, headers=self._auth_headers())
            if not isinstance(page, list):
                raise KeycloakError("User list response was not a JSON array")

            users.extend(page)
            if len(page) < self.page_size:
                return users
            first += self.page_size

    def delete_user(self, user_id: str) -> None:
        user_path = quote(user_id, safe="")
        url = f"{self.base_url}/admin/realms/{self._realm_path}/users/{user_path}"
        self._request("DELETE", url, headers=self._auth_headers(), expect_json=False)

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.get_token()}"}

    def _request(
        self,
        method: str,
        url: str,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
        expect_json: bool = True,
    ) -> Any:
        request = Request(url, data=body, headers=headers or {}, method=method)

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
        except HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise KeycloakError(f"{method} {url} failed with HTTP {exc.code}: {details}") from exc
        except URLError as exc:
            raise KeycloakError(f"{method} {url} failed: {exc.reason}") from exc

        if not expect_json:
            return None
        if not payload:
            return None

        try:
            return json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise KeycloakError(f"{method} {url} returned invalid JSON") from exc
