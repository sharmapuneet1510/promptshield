# PromptShield Repository Structure

## 1. Repository Strategy

PromptShield should use a monorepo layout so that shared logic can be reused cleanly by both Lite and Enterprise editions. This also simplifies contributor onboarding, documentation, versioning, and release management.

The monorepo should separate:

- apps
- shared packages
- deployment assets
- docs
- examples

---

## 2. Top-Level Structure

```text
promptshield/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── SECURITY.md
├── CODE_OF_CONDUCT.md
├── ROADMAP.md
├── .gitignore
├── .env.example
├── Makefile
├── pyproject.toml
├── pnpm-workspace.yaml
├── apps/
├── packages/
├── deploy/
├── docs/
└── examples/
```

---

## 3. Apps Directory

The `apps/` directory contains runnable applications.

```text
apps/
├── promptshield-lite/
├── promptshield-enterprise-api/
└── promptshield-enterprise-ui/
```

---

## 4. PromptShield Lite App

```text
apps/promptshield-lite/
├── README.md
├── pyproject.toml
├── promptshield_lite/
│   ├── __init__.py
│   ├── main.py
│   ├── cli/
│   │   ├── precheck.py
│   │   ├── analyze.py
│   │   ├── config.py
│   │   └── history.py
│   ├── engine/
│   │   ├── token_estimator.py
│   │   ├── prompt_classifier.py
│   │   ├── local_policy_engine.py
│   │   ├── routing_hint_engine.py
│   │   └── local_store.py
│   ├── models/
│   └── output/
└── tests/
```

### Purpose

This app provides the local-only edition. It should support CLI-first usage initially, with optional expansion into desktop or IDE-integrated local tools.

---

## 5. PromptShield Enterprise API App

```text
apps/promptshield-enterprise-api/
├── README.md
├── pyproject.toml
├── promptshield_enterprise/
│   ├── __init__.py
│   ├── main.py
│   ├── settings.py
│   ├── api/
│   │   ├── router.py
│   │   ├── middleware/
│   │   └── v1/
│   │       ├── health.py
│   │       ├── precheck.py
│   │       ├── proxy.py
│   │       ├── analytics.py
│   │       ├── policies.py
│   │       └── admin.py
│   ├── services/
│   │   ├── token_estimator.py
│   │   ├── prompt_classifier.py
│   │   ├── policy_engine.py
│   │   ├── routing_service.py
│   │   ├── quota_service.py
│   │   ├── analytics_service.py
│   │   └── message_service.py
│   ├── providers/
│   ├── storage/
│   ├── telemetry/
│   ├── models/
│   └── rules/
└── tests/
```

### Purpose

This app is the centralized control plane. It exposes APIs for precheck, policy evaluation, proxying, analytics, and admin operations.

---

## 6. PromptShield Enterprise UI App

```text
apps/promptshield-enterprise-ui/
├── README.md
├── package.json
├── src/
│   ├── App.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Requests.tsx
│   │   ├── Policies.tsx
│   │   ├── Users.tsx
│   │   └── Settings.tsx
│   └── components/
└── public/
```

### Purpose

This app provides an administrator-facing interface for monitoring, policy management, and user analytics.

---

## 7. Shared Packages

The `packages/` directory contains reusable modules shared across apps.

```text
packages/
├── promptshield-core/
├── promptshield-config/
└── promptshield-sdk/
```

---

## 8. promptshield-core Package

```text
packages/promptshield-core/
├── README.md
├── pyproject.toml
├── promptshield_core/
│   ├── __init__.py
│   ├── enums.py
│   ├── exceptions.py
│   ├── contracts/
│   ├── schemas/
│   └── utils/
└── tests/
```

### Purpose

This package should contain the shared domain contracts and foundational logic used by both Lite and Enterprise.

---

## 9. promptshield-config Package

```text
packages/promptshield-config/
├── README.md
├── promptshield_config/
│   ├── loader.py
│   ├── validators.py
│   └── defaults/
│       ├── thresholds.yaml
│       ├── routing.yaml
│       ├── exceptions.yaml
│       └── providers.yaml
```

### Purpose

This package centralizes config loading, validation, and defaults.

---

## 10. promptshield-sdk Package

```text
packages/promptshield-sdk/
├── README.md
├── pyproject.toml
├── promptshield_sdk/
│   ├── client.py
│   ├── models.py
│   └── exceptions.py
└── tests/
```

### Purpose

This package provides a reusable SDK for integrations and client applications.

---

## 11. Deployment Assets

```text
deploy/
├── docker/
│   ├── lite.Dockerfile
│   ├── enterprise-api.Dockerfile
│   └── enterprise-ui.Dockerfile
├── compose/
│   └── docker-compose.yml
├── helm/
│   └── promptshield-enterprise/
└── k8s/
```

### Purpose

This directory contains deployment artifacts for local development and production environments.

---

## 12. Documentation

```text
docs/
├── architecture/
├── api/
├── lite/
├── enterprise/
├── deployment/
└── runbooks/
```

### Purpose

The documentation should be organized by topic and audience.

Suggested key files:

- `docs/architecture/architecture.md`
- `docs/architecture/repo-structure.md`
- `docs/lite/getting-started.md`
- `docs/enterprise/getting-started.md`
- `docs/deployment/deployment-guide.md`

---

## 13. Examples

```text
examples/
├── lite-cli-usage/
├── vscode-integration/
├── cloud-code-integration/
└── enterprise-policy-examples/
```

### Purpose

These examples help users adopt the project faster and understand integration patterns.

---

## 14. Why This Structure Works

This repo structure is designed to:

- clearly separate Lite and Enterprise
- maximize code reuse
- keep core logic independent
- support open-source contributions
- make future packaging and release management easier
- support gradual growth from CLI tooling to enterprise platform

---

## 15. Recommended Build Order

1. `packages/promptshield-core`
2. `apps/promptshield-lite`
3. `packages/promptshield-config`
4. `apps/promptshield-enterprise-api`
5. `packages/promptshield-sdk`
6. `apps/promptshield-enterprise-ui`

This order keeps the project grounded in shared logic first and avoids duplication later.

---

## 16. Final Recommendation

Use `promptshield` as the root repo name and keep both editions within the same monorepo until the project becomes large enough to justify splitting repositories.
