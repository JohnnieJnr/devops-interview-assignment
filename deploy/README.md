# deploy/

**This directory is graded.** Your Helm chart or Kubernetes manifests go here.

## What we look for

Something applyable. If we ran `helm install` or `kubectl apply -f` against a real cluster (with the right secrets in place), your manifests would work. You don't have to apply them against the provided Kind cluster.

## Suggested shape

**Helm chart** (preferred, the JD calls Helm out as a required competency):
```
deploy/
  Chart.yaml
  values.yaml
  templates/
    cronjob.yaml
    configmap.yaml
    secret.yaml           # or external-secrets reference
    serviceaccount.yaml
    rbac.yaml
```

**Plain manifests** (fine if you'd rather):
```
deploy/
  cronjob.yaml
  configmap.yaml
  secret.yaml
  ...
```

## Things worth thinking about

- **Where does the Keycloak client secret live?** Not hardcoded in `values.yaml`. Show how you'd reference it: ExternalSecrets, sealed-secrets, an existing Secret name as a value, whatever fits.
- **How does per-realm config flow in?** ConfigMap? Values? Something else?
- **Where does this fit in the sync order?** If you assume ArgoCD, add sync-wave annotations or note where it should land.
- **What service account does the CronJob use, and what RBAC does it need in-cluster?** Note that this Kubernetes SA is separate from the Keycloak service account. The K8s SA is what the CronJob runs as. The Keycloak SA is how it authenticates to Keycloak.
- **What happens if the CronJob fails?** Restart policy, backoff, alerting hooks.

You do not need to build all of this. Pick what matters to you and can defend in the walkthrough. Explain the rest in your README.

## What we don't grade

- Whether your chart passes `helm lint` cleanly (nice, not required)
- Whether the image reference points at a real registry
- Whether you built the container image at all

We care about shape and thinking, not polish.
