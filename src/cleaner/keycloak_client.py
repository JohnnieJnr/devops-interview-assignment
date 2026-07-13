"""Keycloak Admin API client.

Suggested shape:
    - get_token()          - fetch an access token via client_credentials
    - list_users()         - paginate through the realm's users
    - delete_user(user_id) - delete (or disable, if you prefer soft delete)

You can use `python-keycloak`, `requests`, `httpx`, or roll your own.
No requirement — pick whatever fits your approach.
"""


class KeycloakClient:
    def __init__(self, base_url: str, realm: str, client_id: str, client_secret: str):
        self.base_url = base_url
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret

    def get_token(self) -> str:
        # TODO: implement client_credentials token fetch
        raise NotImplementedError

    def list_users(self):
        # TODO: implement paginated user listing
        raise NotImplementedError

    def delete_user(self, user_id: str) -> None:
        # TODO: implement user deletion (or soft-delete via disable — your call)
        raise NotImplementedError
