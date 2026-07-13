# spi/

Placeholder for candidates who choose to implement this as a **Keycloak SPI (Service Provider Interface)** in Java rather than an external tool.

## If you go this route

Put your Maven or Gradle project here. Keycloak SPI is the native extension mechanism. Your code runs inside the Keycloak JVM and can hook into things like:

- **Scheduled tasks** (`org.keycloak.timer.TimerSpi`)
- **User event listeners** (`org.keycloak.events.EventListenerProvider`)
- **User federation providers** (`org.keycloak.storage.UserStorageProvider`)

For the stale-user cleanup task, a **scheduled task provider** is the most direct fit. It lets you register a job that runs on a Keycloak-managed timer.

## Trade-offs to mention in your README

| SPI wins | SPI costs |
|---|---|
| Runs in-process, no external HTTP round-trips | Java toolchain and build required |
| No separate service account needed | Ships coupled to a Keycloak version. Upgrades can break SPIs |
| Direct access to the Keycloak session and user model | Harder to test in isolation |
| Deploys as a single JAR into `providers/` | No separate scaling story. Runs where Keycloak runs |

## Docs pointer

Keycloak SPI reference: https://www.keycloak.org/docs/latest/server_development/#_providers

We haven't scaffolded a Maven project because most candidates go the external-tool route. If you pick SPI, set up your own project structure here.

## Not required

You can do this task without touching SPI. Consideration of SPI, even to reject it with reasoning, is what we look for. Actually building one is one valid path, not the required one.
