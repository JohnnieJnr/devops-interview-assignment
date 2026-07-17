Here's a simpler, more concise version that still covers the six required points.

# Keycloak Stale-User Cleanup

## Purpose

This project cleans up users in the seeded `acme` realm who have been inactive for longer than a configurable retention period (default: **120 days**).

## 1. Approach

I implemented a Python cleanup application that runs as a Kubernetes **CronJob**. It authenticates with Keycloak using the Client Credentials grant, reads the seeded `lastLogin` attribute, and deletes users older than the configured threshold.

I chose this approach because it is simple, lightweight, and uses Keycloak's supported Admin REST API. I did not implement a Keycloak SPI or Kubernetes operator because they add unnecessary complexity for this exercise.

## 2. Kubernetes Deployment

The application is deployed using a Helm chart located in `deploy/keycloak-cleaner/`.

The chart creates:

* CronJob
* ServiceAccount
* Role
* Secret

Deploy:

```bash
helm install keycloak-cleanup ./deploy/keycloak-cleaner
```

Upgrade:

```bash
helm upgrade keycloak-cleanup ./deploy/keycloak-cleaner
```

## 3. Configuration and Safety

Configuration is managed through `values.yaml`.

The cleaner supports:

* configurable retention period (default 120 days)
* dry-run mode
* excluded users
* audit logging through container logs

The Keycloak client secret is stored as a Kubernetes Secret.

## 4. Multi-Realm Extension

The cleanup logic is independent of the realm. Supporting multiple realms would only require adding multiple realm configurations and processing each one in turn.

## 5. Production Improvement

The exercise uses a seeded `lastLogin` user attribute. In production, I would determine inactivity using Keycloak LOGIN events or another authoritative source instead of a custom user attribute.

## 6. AI Usage

AI was used to generate most of the implementation, including the Python code, Helm chart, and documentation. I reviewed the generated code, verified that it met the  requirements, and made corrections where necessary.
