# Keycloak Stale-User Cleanup: Take-home Exercise

Design and ship a mechanism that cleans up users inactive for a configurable period (default 120 days) on Kubernetes. We assess how you deliver it, not whether you match a canonical solution.

## The whole job

1. Build cleanup logic against the seeded `acme` realm (see `keycloak/`)
2. Ship a Helm chart or manifests in [`deploy/`](deploy/) so it can run on Kubernetes
3. Write a one-page README in your repo covering the six points below
4. Fill in [`FEEDBACK.md`](FEEDBACK.md) so we can improve this exercise

**Time cap:** up to three full days. With AI assistance the working version takes well under that. Use the remaining time to understand what you shipped well enough to walk us through it.

## Your one-page README covers

1. Approach chosen, approaches rejected, reasoning
2. How this deploys on K8s (points at `deploy/`)
3. Where per-realm config lives, and safety rails (exclusions, dry-run, audit)
4. How the design would extend to many realms. You don't build it. Show the seam.
5. One thing you'd change in production
6. AI usage. Five to ten lines. Where AI helped, where you accepted its output, where you overrode it.

## Getting started

```bash
cp .env.example .env
make up            # Starts Keycloak + Postgres, imports the seeded realm
make grant-roles   # Grants the service account the realm-management roles
```

Keycloak: `http://localhost:8080`, admin / admin. Realm: `acme`.

Optional, only if you want to test manifests against a real cluster:
```bash
make kind-up
```

## What we assess

| Assessed | Not assessed |
|---|---|
| Approach choice and trade-off reasoning | Whether your Helm chart passes `helm lint` |
| OAuth2 fluency (correct client, correct grant) | Whether the container image builds |
| Deploy shape in `deploy/` (Helm or manifests, applyable) | Test coverage, CI, Dockerfile polish |
| Safety rails (exclusions, dry-run, audit) | Multi-tenancy implementation |
| Tenant-aware seam in the design | Production hardening |
| AI usage maturity (specific, not generic) | Polish |
| Walkthrough performance | Matching a canonical answer |

New to parts of the stack? Fine. Say so in your README, and show us how you learned it.

## The `deploy/` directory is graded

This is where we see your Helm and IaC fluency. Skipping it costs you a whole rubric axis. Details in [`deploy/README.md`](deploy/README.md).

## AI use

Allowed and encouraged. This role will involve working with AI tools going forward, so we want to see you use them well.

In the walkthrough we ask specifically where AI helped, where you accepted its output, and where you pushed back. Prepare specific answers, not generic ones ("used ChatGPT for boilerplate" surfaces as a red flag in the walkthrough).

## What's in this repo

```
.
├── docker-compose.yml           Keycloak + Postgres, realm auto-imported
├── Makefile                     Common commands (run `make help`)
├── .env.example                 Copy to .env
├── kind/                        Optional Kind cluster config
├── keycloak/                    Seeded realm + role-grant script
├── src/cleaner/                 Python skeleton (only if you go Python)
├── deploy/                      GRADED. Your chart or manifests go here.
├── spi/                         Placeholder if you go Java SPI
├── pyproject.toml
└── FEEDBACK.md                  Please fill in
```

## About the seeded `lastLogin` attribute

Keycloak does not natively expose "last login time" as a first-class field. In production you'd use event queries, a login-flow authenticator, or user federation. For this exercise we've seeded a `lastLogin` custom attribute on each user so you can focus on cleanup logic. See [`keycloak/README.md`](keycloak/README.md) for the users and their ages, and mention this simplification in your own README.

## Submitting

Fork this repo, push your work, share the link. Zip is fine if forking is inconvenient. Fork is a small extra signal because the git history shows how you work.

We book the 60-minute walkthrough within a few working days of your submission.

## Questions

Reply to the email thread. Raising questions early is a JD line we mean. Don't sit on ambiguity.

## Done

Your submission is complete when:

- [ ] The code runs against the seeded Keycloak and does what your README says
- [ ] `deploy/` contains an applyable Helm chart or manifest set
- [ ] Your one-page README covers all six points above
- [ ] The AI usage section is specific enough that we could pick which parts you wrote
- [ ] `FEEDBACK.md` is filled in (optional but genuinely useful to us)
