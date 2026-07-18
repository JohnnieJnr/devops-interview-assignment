# deploy/ - Keycloak Cleaner Helm Chart

This directory contains a Helm chart for deploying the Keycloak stale-user cleanup service on Kubernetes.

## Quick Start

### Prerequisites

- Kubernetes cluster 1.24+ (1.27+ for CronJob `timeZone` support)
- Helm 3.x
- A Keycloak instance accessible from the cluster
- A Keycloak client with appropriate realm-management roles

### Local end-to-end test (Kind + docker-compose Keycloak)

From the repo root, with Docker running:

```bash
make helm-test
```

This will:

1. Start Keycloak via `docker compose` and grant service-account roles
2. Create a Kind cluster and load the `cleaner:0.1.0` image
3. Install the chart with `values-kind.yaml` (Keycloak at `host.docker.internal:8080`)
4. Trigger a one-off Job from the CronJob and print its logs

Expected dry-run output: 4 stale candidates (`alice`, `bob`, `carol`, `dave`), `break-glass` skipped, 0 deletions.

Individual steps:

```bash
make up grant-roles      # Keycloak on localhost:8080
make kind-up               # optional if cluster already exists
make image-build           # docker build -t cleaner:0.1.0 .
make helm-install          # kind load + helm upgrade --install
make helm-uninstall        # remove release
```

### Installation (production-shaped)

```bash
# 1. Create a namespace (recommended)
kubectl create namespace keycloak-cleaner

# 2. Create the client secret before installing
kubectl create secret generic keycloak-cleaner-secret \
  --from-literal=client-secret=YOUR_ACTUAL_SECRET \
  -n keycloak-cleaner

# 3. Install the chart into the same namespace
helm install keycloak-cleaner ./keycloak-cleaner -n keycloak-cleaner
```

Resources are deployed into the Helm release namespace (`-n keycloak-cleaner`), not a hardcoded namespace in `values.yaml`.

## Helm Chart Structure

```
keycloak-cleaner/
├── Chart.yaml
├── values.yaml              # Default values (in-cluster Keycloak URL)
├── values-kind.yaml         # Local Kind testing against docker-compose Keycloak
└── templates/
    ├── _helpers.tpl
    ├── cronjob.yaml
    ├── secret.yaml          # Rendered only when secret.create is true
    ├── serviceaccount.yaml
    ├── role.yaml            # Rendered only when rbac.create is true
    └── NOTES.txt
```

## Key Design Decisions

### 1. Client Secret Management

The chart does **not** embed a real client secret in `values.yaml`. By default, `secret.create` is `false` and you provide the Secret out-of-band:

- **Option A (Recommended): Pre-existing Kubernetes Secret**
  - Create the secret manually before installing (see Quick Start)
  - Reference it via `keycloak.clientSecretRef.name` and `keycloak.clientSecretRef.key`

- **Option B: External Secret Store**
  - Use ExternalSecrets, Sealed Secrets, or another GitOps-friendly operator
  - Keep `secret.create: false` and point `clientSecretRef.name` at the operator-managed Secret

- **Option C: Helm-managed Secret (dev/test only)**
  - Set `secret.create: true` and pass the value at install time:
    ```bash
    helm install keycloak-cleaner ./keycloak-cleaner -n keycloak-cleaner \
      --set secret.create=true \
      --set keycloak.clientSecretRef.value=YOUR_ACTUAL_SECRET
    ```

### 2. Per-Realm Configuration

Use one Helm release per realm:

```yaml
keycloak:
  realm: "acme"
  clientId: "user-cleanup-service"
cleanup:
  inactivityDays: 120
  exclusions:
    - admin
    - break-glass
```

```bash
helm install cleaner-acme ./keycloak-cleaner -n keycloak-cleaner --set keycloak.realm=acme
helm install cleaner-partner ./keycloak-cleaner -n keycloak-cleaner --set keycloak.realm=partner-realm
```

### 3. RBAC Configuration

RBAC is **disabled by default** (`rbac.create: false`). The cleaner receives the Keycloak client secret via `secretKeyRef` environment injection, which the kubelet handles — no Kubernetes API access is required at runtime.

Set `rbac.create: true` only if you later mount the secret as a volume and need explicit `secrets/get` permission.

### 4. CronJob Failure Handling

- **Restart Policy**: `OnFailure`
- **Backoff Limit**: 3 retries
- **Active Deadline**: 10 minutes
- **TTL**: 1 hour (completed/failed jobs auto-cleaned)
- **Concurrency Policy**: `Forbid` (no overlapping runs)

### 5. ArgoCD Sync Order

If deploying via ArgoCD, create the client Secret in an earlier sync wave:

```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "2"
```

## Configuration Reference

### Required Setup

```yaml
keycloak:
  url: "http://keycloak.default.svc.cluster.local:8080"
  realm: "acme"
  clientId: "user-cleanup-service"
  clientSecretRef:
    name: "keycloak-cleaner-secret"
    key: "client-secret"
```

A Secret with that name and key must exist in the release namespace before the CronJob runs (unless `secret.create: true`).

### Optional Values

```yaml
secret:
  create: false

cleanup:
  inactivityDays: 120
  dryRun: true                     # Default: safe dry-run mode
  exclusions:
    - admin
    - break-glass

cronjob:
  schedule: "0 2 * * *"
  timeZone: "UTC"
  concurrencyPolicy: "Forbid"
  suspend: false

image:
  repository: "cleaner"
  tag: "0.1.0"
  pullPolicy: "IfNotPresent"

resources:
  requests:
    cpu: "100m"
    memory: "128Mi"
  limits:
    cpu: "500m"
    memory: "256Mi"

serviceAccount:
  create: true

rbac:
  create: false

podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
```

## Deployment Examples

### Example 1: Simple Installation

```bash
kubectl create namespace keycloak-cleaner

kubectl create secret generic keycloak-cleaner-secret \
  --from-literal=client-secret=my-actual-secret \
  -n keycloak-cleaner

helm install cleaner ./keycloak-cleaner -n keycloak-cleaner
```

### Example 2: Dry-Run First

Dry-run is enabled by default. To disable after verification:

```bash
helm upgrade cleaner ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set cleanup.dryRun=false
```

Check logs:

```bash
kubectl logs -n keycloak-cleaner -l app.kubernetes.io/name=keycloak-cleaner --tail=50
```

### Example 3: Multiple Realms

```bash
helm install cleaner-acme ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set keycloak.realm=acme \
  --set keycloak.clientId=user-cleanup-acme \
  --set keycloak.clientSecretRef.name=keycloak-cleaner-acme-secret

helm install cleaner-partner ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set keycloak.realm=partner-realm \
  --set keycloak.clientId=user-cleanup-partner \
  --set keycloak.clientSecretRef.name=keycloak-cleaner-partner-secret
```

## Testing & Verification

### Check CronJob Status

```bash
kubectl get cronjobs -n keycloak-cleaner
kubectl get jobs -n keycloak-cleaner
kubectl logs -n keycloak-cleaner -l app.kubernetes.io/name=keycloak-cleaner --tail=100
```

### Manual Test Run

When the release name matches the chart name (`keycloak-cleaner`), the CronJob resource is also named `keycloak-cleaner`:

```bash
kubectl create job --from=cronjob/keycloak-cleaner \
  keycloak-cleaner-manual-$(date +%s) \
  -n keycloak-cleaner
```

### Validate the Chart Locally

```bash
helm template cleaner ./keycloak-cleaner -n keycloak-cleaner
helm lint ./keycloak-cleaner
```

## Troubleshooting

### Secret Not Found

```bash
kubectl get secret keycloak-cleaner-secret -n keycloak-cleaner
kubectl get secret keycloak-cleaner-secret -n keycloak-cleaner -o jsonpath='{.data}' | jq keys
```

### CronJob Not Running

```bash
kubectl get cronjob -n keycloak-cleaner -o jsonpath='{.items[*].spec.suspend}'
kubectl describe cronjob -n keycloak-cleaner
```

### Connection Errors

```bash
kubectl run -it --rm debug \
  --image=curlimages/curl:latest \
  --restart=Never \
  -n keycloak-cleaner \
  -- curl http://keycloak.default.svc.cluster.local:8080/realms/acme
```

## Security Considerations

The chart runs with:

- Non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- All Linux capabilities dropped

Recommended NetworkPolicy for egress to Keycloak only — see the assignment README for an example.

## Multi-Realm Deployment Design

Current approach: **one Helm release per realm** for isolated config, schedules, and rollback.

Future enhancement: ConfigMap-driven batch processing in a single CronJob would require minor application changes to iterate over realms.
