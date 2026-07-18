# Keycloak Stale-User Cleanup

## Purpose

This project cleans up users in the seeded `acme` realm who have been inactive for longer than a configurable retention period (default: **120 days**).

## 1. Approach

The **solution is a standalone Python script** in `src/cleaner/`. It reads configuration from environment variables, authenticates to Keycloak via Client Credentials, reads the seeded `lastLogin` attribute, and deletes stale users (respecting exclusions and dry-run mode). It has **no Kubernetes dependency** — run it locally, in CI, or from any scheduler.

```bash
cp .env.example .env
make up grant-roles
make run
```

I chose this because it is simple, testable in isolation, and uses Keycloak's Admin REST API. I rejected a Keycloak SPI and a Kubernetes operator as unnecessary complexity for this exercise.

The **Helm chart in `deploy/` is independent** of the Python code. It does not define cleanup logic; it only packages the script for production-style scheduling (CronJob, secrets, service account). You can develop and verify the script without a cluster, then optionally deploy the same container via Helm.

## 2. Kubernetes Deployment

For production (or local cluster testing), the Helm chart schedules the Python script as a CronJob. See `deploy/README.md` for full details.

The chart creates:

- CronJob (runs `python -m cleaner.main` on a schedule)
- ServiceAccount
- Secret reference (create the Secret manually or via ExternalSecrets)

**Local cluster test (Kind + docker-compose Keycloak):**

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

For Kind against host Keycloak, use `values-kind.yaml`.

## 3. Configuration and Safety

**Standalone:** copy `.env.example` to `.env` or export the same variables (`KEYCLOAK_*`, `INACTIVITY_DAYS`, `DRY_RUN`, `EXCLUSIONS`).

**Kubernetes:** the chart maps those same variables into the CronJob pod. Per-realm settings live in Helm `values.yaml` (or `--set` overrides). One Helm release per realm is the intended model.

Safety rails (both modes):

- **Retention threshold** — default 120 days
- **Dry-run** — default `true`; logs candidates without deleting
- **Exclusions** — default `admin`, `break-glass`; service accounts always skipped
- **Audit** — structured JSON logs for each candidate, skip, delete, and summary

In Kubernetes, the client secret comes from a Secret referenced by the chart, not from `values.yaml`.

## 4. Multi-Realm Extension

The Python script is realm-agnostic — pass a different `KEYCLOAK_REALM` (and client credentials) per run. For Kubernetes, deploy one Helm release per realm. A future batch mode could loop over a JSON or ConfigMap list of realm configs without changing the core deletion logic.

## 5. Production Improvement

The exercise uses a seeded `lastLogin` user attribute. In production, I would derive inactivity from Keycloak LOGIN events or a login-flow authenticator, with explicit retention and reconciliation policy.

## 6. AI Usage

AI generated the initial Python client, Helm chart, and README drafts. I reviewed OAuth2 client-credentials flow against the seeded realm, verified exclusion and dry-run behavior against the nine test users, ran the script standalone and via `make helm-test` on Kind, and corrected docs to separate the standalone app from the optional Helm packaging.
