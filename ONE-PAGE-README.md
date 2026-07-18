# Keycloak Stale-User Cleanup

## Purpose

This project cleans up users in the seeded `acme` realm who have been inactive for longer than a configurable retention period (default: **120 days**).

## 1. Approach

I implemented a Python cleanup application that runs as a Kubernetes **CronJob**. It authenticates with Keycloak using the Client Credentials grant, reads the seeded `lastLogin` attribute, and deletes users older than the configured threshold.

I chose this approach because it is simple, lightweight, and uses Keycloak's supported Admin REST API. I rejected a Keycloak SPI and a Kubernetes operator because they add unnecessary complexity for this exercise.

## 2. Kubernetes Deployment

The application is deployed using a Helm chart in `deploy/keycloak-cleaner/`.

The chart creates:

- CronJob (scheduled cleanup)
- ServiceAccount
- Secret (optional — disabled by default; create manually or via ExternalSecrets)

**Local test (Kind + docker-compose Keycloak):**

```bash
make helm-test
```

**Manual install:**

```bash
kubectl create namespace keycloak-cleaner
kubectl create secret generic keycloak-cleaner-secret \
  --from-literal=client-secret=cleanup-secret-change-me -n keycloak-cleaner
helm install keycloak-cleaner ./deploy/keycloak-cleaner -n keycloak-cleaner
```

For Kind against host Keycloak, use `values-kind.yaml` (see `deploy/README.md`).

## 3. Configuration and Safety

Per-realm configuration lives in Helm `values.yaml` (or `--set` overrides). One Helm release per realm is the intended model.

Safety rails:

- **Retention threshold** — `cleanup.inactivityDays` (default 120)
- **Dry-run** — `cleanup.dryRun: true` by default; logs candidates without deleting
- **Exclusions** — `cleanup.exclusions` (default `admin`, `break-glass`); service accounts are always skipped
- **Audit** — structured JSON logs per candidate, skip, delete, and summary event

The Keycloak client secret is stored in a Kubernetes Secret referenced by `keycloak.clientSecretRef`, not embedded in the chart.

## 4. Multi-Realm Extension

The cleanup logic is realm-agnostic. To support many realms, deploy one Helm release per realm with different `keycloak.realm`, `keycloak.clientId`, and secret references. A future single-CronJob design could iterate over a ConfigMap list of realm configs — the application would need a small loop over multiple env blocks or a JSON config file.

## 5. Production Improvement

The exercise uses a seeded `lastLogin` user attribute. In production, I would derive inactivity from Keycloak LOGIN events or a login-flow authenticator, with explicit retention and reconciliation policy, rather than a custom attribute.

## 6. AI Usage

AI generated the initial Python client, CronJob Helm chart, and README drafts. I reviewed OAuth2 client-credentials flow against the seeded realm, verified exclusion and dry-run behavior against the nine test users, ran `make helm-test` end-to-end on Kind, and corrected chart defaults (secret name, local Keycloak URL for Kind, CronJob naming in docs). I kept the stdlib-only HTTP client instead of adding dependencies.
