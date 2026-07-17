# Keycloak Stale-User Cleanup SPI

This directory contains a native Keycloak SPI implementation for stale-user cleanup.

## What is implemented

- `com.example.keycloak.cleanup.CleanupSpi` — SPI registration class
- `UserCleanupProviderFactory` — provider factory that schedules a Keycloak timer task
- `UserCleanupScheduledTask` — cleanup logic that deletes users with stale `lastLogin` attributes
- `META-INF/services/org.keycloak.provider.Spi` — service registration for Keycloak provider discovery

## Build

From `spi/`:

```bash
mvn package -DskipTests
```

The resulting JAR is `target/keycloak-user-cleanup-spi-0.1.0.jar`.

## Deployment

Drop the built JAR into Keycloak's `providers/` directory and restart Keycloak.

## Configuration

The provider supports the following server configuration keys in `keycloak.conf` or `keycloak-server.json`:

- `threshold-days` (default `120`)
- `schedule-interval-minutes` (default `1440`)
- `realm-name` (default `acme`)
- `exclude-users` (default `break-glass`)
- `dry-run` (default `false`)
