# PromptShield Architecture

## 1. Architecture Overview

PromptShield is designed as a dual-mode product family with a shared logic core and two primary editions:

- **PromptShield Lite** for local, client-first usage
- **PromptShield Enterprise** for centralized governance and enforcement

The architecture should maximize logic reuse while keeping Lite simple and Enterprise scalable.

---

## 2. Design Principles

1. Keep the hot path lightweight.
2. Use deterministic logic first.
3. Keep configuration externalized.
4. Separate reusable logic from deployment-specific concerns.
5. Support graceful evolution from local-only to centralized governance.
6. Minimize latency added before a model call.
7. Design Enterprise for horizontal scaling and operational visibility.

---

## 3. Product Architecture

```text
PromptShield
├── Shared Core
│   ├── token estimation
│   ├── prompt classification
│   ├── policy evaluation
│   ├── routing logic
│   ├── contracts and schemas
│   └── message construction
├── PromptShield Lite
│   ├── CLI
│   ├── local desktop app
│   ├── IDE/plugin integration
│   └── local storage and insights
└── PromptShield Enterprise
    ├── API / control plane
    ├── provider proxy
    ├── centralized policy
    ├── analytics and audit
    └── admin UI
```

---

## 4. Shared Core

The shared core should be reusable by both editions and include:

- request/response schemas
- decision enums
- token estimation services
- prompt classification services
- policy evaluation engine
- route decision logic
- message generation helpers
- validation utilities

The shared core must remain independent of any specific UI or transport layer.

---

## 5. PromptShield Lite Architecture

PromptShield Lite runs locally and is primarily advisory.

### 5.1 Components

- Local CLI
- Optional desktop UI
- Local rules/config loader
- Token estimator
- Prompt classifier
- Local policy engine
- Local routing hint engine
- Local history store

### 5.2 Flow

```text
User prompt
  -> local precheck
  -> token estimate
  -> cost estimate
  -> prompt classification
  -> local policy evaluation
  -> user guidance / routing hint
  -> optional local history
```

### 5.3 Storage

Lite may use:

- JSON files
- SQLite
- in-memory cache

Lite should not require central infrastructure.

---

## 6. PromptShield Enterprise Architecture

PromptShield Enterprise is a centralized, policy-driven control plane.

### 6.1 Core Components

- API gateway / control plane
- shared core engine
- centralized configuration loader
- policy service
- quota service
- routing service
- provider adapters
- logging and analytics service
- audit service
- admin UI

### 6.2 Data Layer

Recommended storage:

- **PostgreSQL** for durable records, analytics, audit
- **Redis** for rate limiting, counters, caching, transient state

### 6.3 Enterprise Request Flow

```text
Client / IDE / MCP / app
  -> Enterprise API
  -> request validation
  -> token estimation
  -> prompt classification
  -> policy evaluation
  -> decision + message creation
  -> optional route override
  -> logging / counters
  -> optional provider proxy
  -> response
```

### 6.4 Enterprise Decision Types

- ALLOW
- WARN
- BLOCK
- REROUTE_WEBSEARCH
- REROUTE_CHEAPER_MODEL
- REQUIRE_CONFIRMATION

---

## 7. Provider Integration Layer

The architecture should support multiple model providers.

### 7.1 Provider Adapters

Adapters should encapsulate provider-specific logic such as:

- API endpoint handling
- auth and API keys
- pricing metadata
- response normalization
- usage metadata parsing

### 7.2 Initial Providers

- OpenAI-compatible APIs
- Anthropic
- Ollama / local model providers
- optional web-search route

---

## 8. Configuration Architecture

Configuration should remain externalized and versionable.

### 8.1 Primary Config Areas

- thresholds
- routing rules
- provider pricing
- exception and warning messages
- user/team overrides
- logging policy
- retention controls

### 8.2 Recommended Config Files

- `thresholds.yaml`
- `routing.yaml`
- `exceptions.yaml`
- `providers.yaml`

Enterprise should support auditable updates to these settings.

---

## 9. Analytics Architecture

PromptShield should track both immediate decisions and long-term behavior.

### 9.1 Key Metrics

- request count
- estimated tokens
- estimated cost
- allow/warn/block counts
- reroute frequency
- model usage mix
- misuse patterns
- user/team trends

### 9.2 Misuse Detection

The system should support a misuse score using signals like:

- repeated blocked requests
- oversized prompts
- repeated search-like prompts to premium models
- repeated bypass behavior
- duplicate prompts
- wasteful usage ratios

---

## 10. Security and Privacy

### 10.1 Lite

- local-first
- prompt history should be transparent and controllable
- no unnecessary remote persistence

### 10.2 Enterprise

- protect admin APIs
- protect provider credentials
- redact or hash sensitive prompt data where required
- make raw prompt storage optional
- preserve audit trails for policy changes

---

## 11. Observability

Enterprise should support:

- structured logs
- metrics
- traces
- provider latency visibility
- decision-rate dashboards
- error-rate monitoring

---

## 12. Scalability Strategy

### 12.1 Lite

Lite should scale per user machine and remain lightweight.

### 12.2 Enterprise

Enterprise should be designed as stateless application nodes behind a load balancer, with shared Redis and Postgres.

Key principles:

- horizontal API scaling
- minimal synchronous work in the hot path
- fast config reads
- limited DB writes per request
- background rollups for analytics

---

## 13. Future Architecture Extensions

Potential future additions:

- IDE extensions
- MCP server
- VS Code integration
- admin dashboard enhancements
- ML-assisted classifier
- managed cloud deployment
- fine-grained org policy packs

---

## 14. Architecture Summary

PromptShield should be architected as a shared-core platform with:

- **Lite** for local, fast, privacy-friendly prompt guidance
- **Enterprise** for centralized governance, control, and analytics

This design allows the project to begin small while growing into a serious production-grade open-source platform.
