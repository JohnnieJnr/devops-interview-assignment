# Keycloak seed data

## What's here

- `realm-export.json`: one realm (`acme`) with:
  - One confidential service client `user-cleanup-service` (client_credentials, secret `cleanup-secret-change-me`)
  - One public client `acme-portal` (illustrative, not required for the task)
  - Nine users with a `lastLogin` custom attribute set to various ages
- `grant-service-account-roles.sh`: runs after realm import to grant the service account the roles it needs (view-users, manage-users, query-users, view-events)

## The `lastLogin` attribute is a deliberate simplification

Keycloak does not natively expose "last login time" as a first-class user field. In production you'd typically use one of:

1. **Event logging.** Keycloak stores `LOGIN` events (when enabled) and you can query them via `/admin/realms/{realm}/events?type=LOGIN&user={id}`. Downside: events have retention limits.
2. **Custom user federation.** Store the last login time in an external store updated on each successful auth.
3. **A login flow authenticator (SPI).** Custom Authenticator SPI that updates a user attribute on every login.

For this exercise we've seeded a `lastLogin` user attribute directly, so you can focus on the cleanup logic rather than building the login-tracking mechanism. Mention in your README that this simplification exists and what you'd do differently in production.

If you'd rather use event-based lookup, the realm has events enabled. The seeded users won't have login events (they've never actually logged in), but the mechanism is available.

## User ages (as seeded)

| Username    | lastLogin (days ago) | Expected outcome at default 120-day threshold |
|-------------|----------------------|-----------------------------------------------|
| alice       | 200                  | DELETE                                        |
| bob         | 180                  | DELETE                                        |
| carol       | 150                  | DELETE                                        |
| dave        | 121                  | DELETE (just over threshold)                  |
| eve         | 119                  | KEEP (just under threshold)                   |
| frank       |  90                  | KEEP                                          |
| grace       |  30                  | KEEP                                          |
| heidi       |   5                  | KEEP                                          |
| break-glass | 400                  | KEEP (excluded despite age)                   |

The `break-glass` user is deliberately old to test that your exclusion logic actually excludes.

## Roles granted to the service account

The `grant-service-account-roles.sh` script grants the following `realm-management` client roles to the service account of `user-cleanup-service`:

| Role | Purpose |
|---|---|
| `view-users` | list and read users |
| `manage-users` | update and delete users |
| `query-users` | search users |
| `view-events` | read login events (if you use the event-based approach) |

## Verifying access

Once `make up` and `make grant-roles` have completed:

```bash
# Get a token
TOKEN=$(curl -s -X POST http://localhost:8080/realms/acme/protocol/openid-connect/token \
  -d grant_type=client_credentials \
  -d client_id=user-cleanup-service \
  -d client_secret=cleanup-secret-change-me | jq -r .access_token)

# List users
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/admin/realms/acme/users | jq '.[].username'
```
