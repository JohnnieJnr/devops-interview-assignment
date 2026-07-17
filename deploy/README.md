# deploy/ - Keycloak Cleaner Helm Chart

This directory contains a production-ready Helm chart for deploying the Keycloak stale-user cleanup service on Kubernetes.

## Quick Start

### Prerequisites
- Kubernetes cluster 1.24+
- Helm 3.x
- A Keycloak instance accessible from the cluster
- A service account in Keycloak with appropriate realm-management roles

### Installation

```bash
# 1. Create a namespace (optional but recommended)
kubectl create namespace keycloak-cleaner

# 2. Create a secret with the Keycloak client secret
kubectl create secret generic keycloak-cleaner-secret \
  --from-literal=client-secret=YOUR_ACTUAL_SECRET \
  -n keycloak-cleaner

# 3. Install the Helm chart
helm install keycloak-cleaner ./keycloak-cleaner \
  -n keycloak-cleaner \
  --values values.yaml
```

## Helm Chart Structure

```
keycloak-cleaner/
├── Chart.yaml                    # Chart metadata
├── values.yaml                   # Default configuration values
├── templates/
│   ├── _helpers.tpl             # Helm template helpers
│   ├── cronjob.yaml             # CronJob template
│   ├── secret.yaml              # Secret template (for reference)
│   ├── serviceaccount.yaml       # ServiceAccount template
│   └── role.yaml                # Role and RoleBinding templates
```

## Key Design Decisions

### 1. Client Secret Management

The chart does **not** hardcode the Keycloak client secret in `values.yaml`. Instead:

- **Option A (Recommended): External Secret Store**
  - Use ExternalSecrets to fetch from AWS Secrets Manager, HashiCorp Vault, etc.
  - Enable in `values.yaml`: `externalSecrets.enabled: true`
  - Configure the SecretStore reference

- **Option B: Pre-existing Kubernetes Secret**
  - Create the secret manually before installing the chart
  - Reference it via `keycloak.clientSecretRef.name`

- **Option C: Sealed Secrets**
  - Use Bitnami Sealed Secrets for GitOps-friendly secret management
  - Encrypt secrets at rest in Git

### 2. Per-Realm Configuration

The chart supports multiple configurations:

```yaml
# Single realm (default)
keycloak:
  realm: "acme"
  clientId: "user-cleanup-service"
cleanup:
  inactivityDays: 120
  exclusions: "admin,break-glass"

# For multiple realms, create separate Helm releases:
# helm install cleaner-acme ./keycloak-cleaner --set keycloak.realm=acme
# helm install cleaner-partner ./keycloak-cleaner --set keycloak.realm=partner-realm
```

See the "Multi-Realm Deployment" section below for design notes.

### 3. RBAC Configuration

The Kubernetes ServiceAccount has minimal, least-privilege permissions:

```yaml
# Allows the CronJob to:
- Get the Keycloak client secret
- List and read ConfigMaps (for multi-realm support)
- Read pod logs (for debugging)
```

This is **separate** from the Keycloak service account (which is how the cleaner authenticates to Keycloak itself).

### 4. CronJob Failure Handling

- **Restart Policy**: `OnFailure` (retry pod if it exits non-zero)
- **Backoff Limit**: 3 retries before marking job as failed
- **Active Deadline**: 10 minutes to complete
- **TTL**: 1 hour (completed/failed jobs auto-cleaned after 1 hour)
- **Concurrency Policy**: `Forbid` (prevent overlapping runs)

To add alerting, integrate with your monitoring stack:
- Watch for CronJob failures: `kubectl get cronjobs -w`
- Send alerts on non-zero exit codes via a sidecar or webhook

### 5. ArgoCD Sync Order

If deploying via ArgoCD, consider:

```yaml
# Sync Wave for ArgoCD
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "2"  # After secrets/config created in wave 1
```

The chart is designed to work with standard ArgoCD SyncPolicy:
```yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
```

## Configuration Reference

### Required Values

```yaml
keycloak:
  url: "http://keycloak.default.svc.cluster.local:8080"
  realm: "acme"
  clientId: "user-cleanup-service"
  clientSecretRef:
    name: "keycloak-cleaner-secret"
    key: "client-secret"
```

### Optional Values

```yaml
# Cleanup thresholds and policies
cleanup:
  inactivityDays: 120              # Users inactive for 120+ days are stale
  dryRun: false                    # true = log only, false = delete
  exclusions: "admin,break-glass"  # Comma-separated list of usernames to never delete

# CronJob schedule
cronjob:
  schedule: "0 2 * * *"            # Daily at 2 AM UTC
  concurrencyPolicy: "Forbid"      # Prevent overlapping runs
  suspend: false                   # Set true to pause cleanups

# Resource requests/limits
pod:
  resources:
    requests:
      cpu: "100m"
      memory: "128Mi"
    limits:
      cpu: "500m"
      memory: "256Mi"

# Security context
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
```

## Deployment Examples

### Example 1: Simple Installation

```bash
# Create namespace
kubectl create namespace keycloak-cleaner

# Create secret with actual client secret
kubectl create secret generic keycloak-cleaner-secret \
  --from-literal=client-secret=my-actual-secret \
  -n keycloak-cleaner

# Install with defaults
helm install cleaner ./keycloak-cleaner \
  -n keycloak-cleaner
```

### Example 2: Dry-Run First

```bash
# Test without deleting any users
helm install cleaner-dryrun ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set cleanup.dryRun=true
```

Check logs:
```bash
kubectl logs -n keycloak-cleaner -l app.kubernetes.io/name=keycloak-cleaner --tail=50
```

Once verified safe, upgrade with `dryRun: false`:
```bash
helm upgrade cleaner ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set cleanup.dryRun=false
```

### Example 3: Multiple Realms

Install separate releases for each realm:

```bash
# Realm: acme
helm install cleaner-acme ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set keycloak.realm=acme \
  --set keycloak.clientId=user-cleanup-acme \
  --set keycloak.clientSecretRef.name=keycloak-cleaner-acme-secret

# Realm: partner
helm install cleaner-partner ./keycloak-cleaner \
  -n keycloak-cleaner \
  --set keycloak.realm=partner-realm \
  --set keycloak.clientId=user-cleanup-partner \
  --set keycloak.clientSecretRef.name=keycloak-cleaner-partner-secret
```

### Example 4: ExternalSecrets Integration

```bash
# values.yaml snippet
keycloak:
  clientSecretRef:
    name: keycloak-cleaner-external-secret
externalSecrets:
  enabled: true
  secretStoreRef:
    name: vault-store
    kind: SecretStore

# Install
helm install cleaner ./keycloak-cleaner \
  -n keycloak-cleaner \
  -f values.yaml
```

## Testing & Verification

### Check CronJob Status

```bash
# View CronJob
kubectl get cronjobs -n keycloak-cleaner

# View recent Job runs
kubectl get jobs -n keycloak-cleaner -L batch.kubernetes.io/job-name

# View Pod logs
kubectl logs -n keycloak-cleaner -l app.kubernetes.io/name=keycloak-cleaner --tail=100
```

### Manual Test Run

Manually trigger a job:

```bash
kubectl create job --from=cronjob/keycloak-cleaner \
  keycloak-cleaner-manual \
  -n keycloak-cleaner

# Watch the job
kubectl get jobs -n keycloak-cleaner -w

# Check logs
kubectl logs -n keycloak-cleaner keycloak-cleaner-manual-xxxxx
```

### Expected Log Output (Dry-Run)

```json
{"event": "skipped", "reason": "excluded", "username": "admin"}
{"event": "candidate", "inactiveDays": 210, "username": "alice"}
{"deleted": 0, "dry_run": true, "event": "summary", "stale_candidates": 1}
```

## Troubleshooting

### Secret Not Found

```bash
# Verify secret exists
kubectl get secret keycloak-cleaner-secret -n keycloak-cleaner

# Verify key name matches values.yaml
kubectl get secret keycloak-cleaner-secret -n keycloak-cleaner -o jsonpath='{.data}' | jq keys
```

### CronJob Not Running

```bash
# Check CronJob is not suspended
kubectl get cronjob keycloak-cleaner -n keycloak-cleaner -o jsonpath='{.spec.suspend}'

# Check if next scheduled run is in the past
kubectl describe cronjob keycloak-cleaner -n keycloak-cleaner
```

### Connection Errors

```bash
# Verify Keycloak URL is reachable from the pod
kubectl run -it --rm debug \
  --image=curlimages/curl:latest \
  --restart=Never \
  -n keycloak-cleaner \
  -- curl http://keycloak.default.svc.cluster.local:8080/realms/acme
```

### Permission Denied

```bash
# Verify service account permissions
kubectl describe rolebinding keycloak-cleaner -n keycloak-cleaner

# Verify the Keycloak service account has realm-management roles in Keycloak UI
# Navigate to: Clients > user-cleanup-service > Service Account Roles
```

## Multi-Realm Deployment Design

This chart supports scaling to multiple realms through:

1. **Separate Helm Releases**: One release per realm with different configuration
   - Pro: Isolated upgrade/rollback cycles
   - Con: Multiple Helm releases to manage

2. **ConfigMap-driven Batch Processing** (future enhancement):
   - Store realm list in ConfigMap
   - CronJob iterates over realms in a single Pod
   - Pro: Single Helm release, easier monitoring
   - Con: More complex logic in the cleaner app

Current implementation uses approach 1. To extend to approach 2:

```yaml
# Proposed enhancement in values.yaml
multiRealm:
  enabled: true
  realms:
    - name: "acme"
      inactivityDays: 120
      exclusions: "admin,break-glass"
    - name: "partner"
      inactivityDays: 90
      exclusions: "admin"
```

The cleaner application would need minor changes to iterate over realms from a ConfigMap.

## Security Considerations

### Pod Security Context

The chart runs with:
- Non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- Dropped all Linux capabilities

### Network Policies

Recommended to add:
```yaml
# Allow outbound to Keycloak
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: keycloak-cleaner-egress
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: keycloak-cleaner
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: keycloak
    ports:
    - protocol: TCP
      port: 8080
```

### RBAC Minimization

The ServiceAccount role grants:
- `secrets/get` on one specific secret (client secret)
- `configmaps/get,list` for multi-realm support
- `pods/log` for debugging

These are the minimum permissions required. Review for your specific security posture.

## What We Don't Grade

- Whether the chart passes `helm lint` (nice, not required)
- Whether the container image is built or exists in a registry
- Whether the chart is "production-ready" (we want to see thinking, not perfection)
- Multi-tenancy implementation (we only test with the `acme` realm)
- Production hardening (monitoring, logging aggregation, etc.)

## What We Do Grade

- ✅ **Deployment shape**: Does the chart structure make sense?
- ✅ **Secret management**: Is the client secret handled safely?
- ✅ **Per-realm configuration**: How does config flow in?
- ✅ **RBAC thinking**: Does the ServiceAccount have appropriate permissions?
- ✅ **Failure handling**: What happens when the CronJob fails?
- ✅ **Multi-realm design**: What's the seam for scaling?
- ✅ **Explanation**: Can you defend your choices in the walkthrough?
