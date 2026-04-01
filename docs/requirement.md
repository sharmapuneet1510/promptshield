# PromptShield Requirements

## 1. Overview

**PromptShield** is an open-source prompt governance and query intelligence platform designed to improve how individuals and organizations use LLMs. The platform should help users understand prompt size, estimated token usage, probable cost, and likely best route before a request is sent to an expensive model. It should also help organizations enforce policy, reduce waste, improve prompt quality, and identify poor usage patterns over time.

The product line will support two primary operating modes:

- **PromptShield Lite**: a client-first, lightweight edition for individual users and local environments.
- **PromptShield Enterprise**: a centralized control-plane edition for teams and organizations that require policy enforcement, analytics, routing, quotas, and auditability.

The system should be designed so that both editions share a common conceptual model, while differing in architecture, enforcement strength, and operational complexity.

---

## 2. Vision

PromptShield should become a practical and production-grade governance layer for AI usage. The aim is not only to estimate tokens, but to help users make better choices before they consume model resources. The product should encourage responsible and efficient use of AI, especially in environments where developers increasingly rely on coding assistants, chat-based tools, MCP servers, agentic workflows, and premium cloud models.

The long-term vision is for PromptShield to act as:

- a **prompt pre-check engine**,
- a **policy and routing layer**,
- a **user coaching and behavior analytics system**,
- and, in enterprise mode, a **centralized AI governance platform**.

---

## 3. Problem Statement

Organizations and individual users face several problems when working with LLMs:

1. Prompts are often sent without any awareness of their estimated size or cost.
2. Premium models are often used for generic, search-like, or low-value queries.
3. There is no consistent way to warn a user before a wasteful request is submitted.
4. Organizations cannot easily enforce standards across multiple tools and users.
5. Poor usage patterns are difficult to identify and correct.
6. Existing tools tend to focus on post-hoc billing rather than pre-query guidance.
7. In many cases, users are using coding models as search engines or general-purpose assistants for tasks that could be routed more cheaply or more appropriately.

PromptShield is intended to solve these problems by adding a decision layer before the model call happens.

---

## 4. Product Editions

### 4.1 PromptShield Lite

PromptShield Lite is the local, client-first edition. It should be lightweight, easy to install, privacy-friendly, and fast.

The Lite edition should support:

- local prompt analysis,
- local token estimation,
- local prompt classification,
- local warning messages,
- local routing suggestions,
- optional local history storage,
- optional local usage insights,
- and integration with CLI tools, local desktop UI, IDE plugins, or local MCP clients.

Lite should avoid requiring centralized infrastructure. It is primarily a productivity and education tool, not a strict enforcement layer.

### 4.2 PromptShield Enterprise

PromptShield Enterprise is the centralized control-plane edition. It should provide a policy-driven gateway and management plane for teams and organizations.

The Enterprise edition should support:

- centralized prompt pre-check,
- configurable policy enforcement,
- user and team quotas,
- shared routing rules,
- provider proxying,
- query logging,
- usage analytics,
- misuse detection,
- admin controls,
- configuration management,
- audit trail,
- and operational observability.

Enterprise should be suitable for deployment as a service used by many users, teams, or applications.

---

## 5. Core Goals

PromptShield should achieve the following goals:

1. **Pre-query intelligence**: estimate likely token usage and cost before sending the prompt.
2. **Prompt quality guidance**: help the user understand if the prompt is overly broad, vague, oversized, or poorly suited to the selected model.
3. **Efficient routing**: suggest or enforce sending the request to a more suitable destination, such as web search or a cheaper model.
4. **Usage governance**: allow organizations to define and apply policies.
5. **Behavior analytics**: identify repeated misuse patterns and improvement opportunities.
6. **Low-latency operation**: keep the hot path lightweight.
7. **Open-source usability**: be installable, understandable, and extensible by the community.
8. **Dual-mode design**: support both local-only and centralized enterprise operation.

---

## 6. Non-Goals

PromptShield is not intended to be:

- a replacement for the underlying LLM provider,
- a full general-purpose chatbot UI by itself,
- a deep model quality evaluator,
- a full billing platform,
- or a heavy workflow orchestration engine in its initial versions.

It may integrate with such systems later, but the primary focus is pre-query governance and decision support.

---

## 7. Primary User Personas

### 7.1 Individual Developer

An engineer using an IDE, CLI, coding assistant, or local chat tool who wants to understand whether a query is too large, too generic, or too expensive before sending it.

### 7.2 Team Lead / Platform Owner

A technical lead who wants to reduce model waste, improve team usage quality, and guide engineers toward better prompting practices.

### 7.3 Enterprise Administrator

An administrator or platform engineer responsible for rolling out AI governance, quotas, logging, routing, and audit across the organization.

### 7.4 AI Governance / FinOps Stakeholder

A stakeholder who wants visibility into waste, usage patterns, cost hot spots, and training opportunities.

---

## 8. Functional Requirements

### 8.1 Prompt Input Handling

The system must accept a prompt request with, at minimum:

- prompt text,
- requested model,
- user identifier,
- optional team identifier,
- source of request,
- optional metadata such as project, repository, or session.

The system should be able to operate in pre-check mode only, or in pre-check plus proxy mode.

### 8.2 Token Estimation

The system must estimate input tokens before execution.

The system should also estimate likely output tokens using configurable heuristics or provider-specific assumptions.

The estimation logic should:

- prefer provider-accurate tokenizers where possible,
- fall back to heuristics where necessary,
- be fast enough for hot-path usage,
- be clearly marked as an estimate, not exact billing truth.

### 8.3 Cost Estimation

The system must calculate an estimated request cost based on:

- selected model,
- estimated input tokens,
- estimated output tokens,
- and configurable pricing tables.

The pricing configuration should be overridable and versionable.

### 8.4 Prompt Classification

The system must classify prompts into one or more categories.

Initial categories should include:

- coding,
- documentation,
- generic,
- search-like,
- oversized,
- broad-scope,
- repetitive,
- and other categories that help route or guide the user.

The initial implementation should be rule-based. Later versions may optionally support small-model or ML-assisted classification.

### 8.5 Policy Evaluation

The system must evaluate the request against configurable rules.

Rules may include:

- maximum input token threshold,
- maximum estimated cost threshold,
- daily request count limit,
- daily spend limit,
- model restrictions,
- routing requirements,
- source-specific rules,
- user or team-specific overrides,
- bypass permissions,
- and warning vs blocking behavior.

The policy engine must support at least the following decisions:

- `ALLOW`
- `WARN`
- `BLOCK`
- `REROUTE_WEBSEARCH`
- `REROUTE_CHEAPER_MODEL`
- `REQUIRE_CONFIRMATION`

### 8.6 Messaging and Guidance

The system must produce clear, configurable warning or exception messages.

Examples include:

- the prompt appears too broad,
- the prompt is better suited to web search,
- estimated cost exceeds threshold,
- the request is too large,
- the user is approaching quota,
- or repeated inefficient usage has been detected.

Messages must be configurable so organizations can define their own wording.

### 8.7 Routing

The system must support route suggestions in Lite mode and route enforcement in Enterprise mode.

Potential routes include:

- continue to requested model,
- reroute to cheaper model,
- reroute to local model,
- reroute to web search,
- block,
- or ask for confirmation.

### 8.8 Query Logging

The system must support logging of requests, decisions, and key metadata.

Logging requirements differ by edition:

- Lite may store only local history and user-visible insights.
- Enterprise must support durable structured storage for analytics, governance, and audit.

The system should support raw prompt storage as configurable and optional, since privacy and security requirements vary.

### 8.9 Usage Analytics

The system should provide analytics around:

- request volume,
- estimated token volume,
- estimated spend,
- model distribution,
- frequency of reroutes,
- frequency of blocks,
- repeated misuse patterns,
- and user or team trends over time.

### 8.10 Misuse Detection and Coaching

The system should identify users who repeatedly submit poor-fit or wasteful queries.

Misuse indicators may include:

- repeated blocked prompts,
- frequent oversized prompts,
- repeated search-like prompts to premium coding models,
- repeated bypass after warning,
- duplicate or near-duplicate submissions,
- and unusually high cost with little evidence of efficient use.

The system should compute a misuse score or equivalent summary that can support user coaching.

### 8.11 Configuration Management

The system must support configuration-driven behavior.

Core configuration areas include:

- thresholds,
- routing rules,
- provider pricing,
- exception/warning messages,
- model metadata,
- user/team overrides,
- and logging behavior.

Enterprise edition should support versioned and auditable config changes.

### 8.12 Integrations

The system should support integration patterns such as:

- local CLI,
- desktop app,
- IDE integration,
- MCP integration,
- HTTP API,
- provider proxy mode,
- and optional web-search routing.

---

## 9. Lite Edition Requirements

### 9.1 Installation and Packaging

PromptShield Lite should be easy to install as:

- a pip package,
- a CLI,
- a local desktop app,
- or a reusable SDK.

### 9.2 Local Operation

Lite should operate without requiring a central backend.

It should:

- perform all prompt checks locally,
- store data locally if history is enabled,
- allow optional local config,
- and remain usable offline except where external routing is requested.

### 9.3 Performance

Lite checks should complete with minimal local delay and should feel near-instant for normal prompts.

### 9.4 Privacy

Lite should default to keeping analysis local.

Any local logging should be transparent and user-controllable.

### 9.5 Suggestive, Not Heavy-Handed

Lite should primarily guide rather than enforce. It may block extreme cases if configured, but its default behavior should be advisory.

---

## 10. Enterprise Edition Requirements

### 10.1 Centralized API Layer

Enterprise must expose an API for:

- pre-check only,
- pre-check plus proxy,
- admin operations,
- analytics,
- policy management,
- and health/observability.

### 10.2 Centralized Enforcement

Enterprise must be able to enforce policy regardless of the client.

### 10.3 Quotas and Controls

Enterprise must support per-user and per-team usage controls.

### 10.4 Durable Storage

Enterprise must persist requests, decisions, usage data, and audit events in durable storage.

### 10.5 Multi-User Visibility

Enterprise must provide dashboards or APIs for administrators to review usage, behavior patterns, and policy outcomes.

### 10.6 Auditability

Enterprise must record:

- config changes,
- policy changes,
- administrative actions,
- and significant system decisions.

### 10.7 Scalability

Enterprise must be able to scale horizontally and support large request volumes.

---

## 11. Non-Functional Requirements

### 11.1 Performance

- Pre-check operations should be low latency.
- Hot-path logic should remain lightweight.
- Token estimation and policy evaluation should not depend on heavy models in the initial implementation.

### 11.2 Scalability

- Lite should remain lightweight on local machines.
- Enterprise should support high concurrency and horizontal scaling.
- The design should support millions of requests over time.

### 11.3 Reliability

- Enterprise should degrade gracefully if a downstream provider is unavailable.
- Pre-check should still function even if proxy mode or a provider is down.

### 11.4 Security

- Sensitive data handling must be configurable.
- Administrative operations must be protected.
- Secrets and provider keys must not be exposed to clients unnecessarily.

### 11.5 Observability

Enterprise should support logs, metrics, and traces that allow operational monitoring and debugging.

---

## 12. Architectural Principles

1. Keep the hot path simple.
2. Prefer deterministic and explainable rules first.
3. Make behavior configuration-driven.
4. Support both local-only and centralized deployment modes.
5. Minimize overhead for individual users.
6. Make enterprise mode auditable and extensible.
7. Separate shared logic from deployment-specific features.

---

## 13. High-Level Architecture

### 13.1 Shared Core

A shared core should contain:

- request models,
- token estimation,
- classification,
- policy evaluation,
- routing logic,
- decision models,
- and message construction.

### 13.2 Lite Architecture

Lite should be client-first. Typical flows may include:

- CLI to local engine,
- desktop UI to local engine,
- IDE/plugin to local engine,
- local storage for logs/history.

### 13.3 Enterprise Architecture

Enterprise should include:

- API gateway / control-plane service,
- shared rule engine,
- centralized storage,
- provider adapters,
- analytics services,
- and admin-facing configuration and reporting.

---

## 14. Data and Privacy Requirements

The system should support multiple storage strategies.

Possible fields for persisted request records include:

- request id,
- user id,
- team id,
- timestamp,
- source,
- model,
- estimated input tokens,
- estimated output tokens,
- estimated total tokens,
- estimated cost,
- decision,
- classifications,
- prompt hash,
- redacted prompt,
- optional raw prompt,
- misuse score,
- and route taken.

Raw prompt persistence should be optional and controlled by policy.

---

## 15. Proposed Decision Flow

1. Receive request.
2. Validate input.
3. Estimate tokens.
4. Estimate cost.
5. Classify prompt.
6. Evaluate policy.
7. Build messages and allowed actions.
8. Suggest or enforce route.
9. Log decision and metadata.
10. If in proxy mode and allowed, forward to provider.
11. Record result or downstream usage if available.

---

## 16. Example Behaviors

### Example 1: Generic Search-Like Query

A user asks a premium coding model for broad public information. The system detects a search-like pattern, warns the user, and suggests web search or reroutes in enterprise mode.

### Example 2: Oversized Prompt

A user pastes an extremely large prompt. The system estimates the token count, detects threshold violation, and blocks or warns depending on policy.

### Example 3: Frequent Misuse

A user repeatedly sends generic prompts to a premium model. The system records the pattern, assigns a misuse score, and surfaces the user in daily analytics.

---

## 17. Repository Strategy

The repository should be organized as a product family with shared components and separate applications for Lite and Enterprise. The shared core must be reusable by both editions.

At a high level, the repo should include:

- shared core packages,
- Lite app(s),
- Enterprise app(s),
- documentation,
- deployment manifests,
- examples,
- tests,
- and configuration samples.

---

## 18. Milestones

### Phase 1

- shared core models,
- local token estimation,
- local prompt classification,
- local pre-check,
- CLI prototype,
- and requirement/documentation foundation.

### Phase 2

- Lite desktop/UI experience,
- local history and insights,
- improved configurability,
- packaging and release process.

### Phase 3

- Enterprise API,
- durable storage,
- centralized policy,
- analytics,
- proxy mode,
- admin controls.

### Phase 4

- advanced integrations,
- richer dashboards,
- optional ML-assisted classification,
- broader ecosystem adoption.

---

## 19. Success Criteria

The project should be considered successful if it can:

- help users understand prompt size and cost before execution,
- reduce wasteful use of expensive models,
- route obvious generic queries more appropriately,
- identify repeated misuse patterns,
- work well for both individuals and organizations,
- and be perceived as a serious, production-grade open-source solution rather than a hobby utility.

---

## 20. Open Questions

1. Which client integrations should be prioritized first: CLI, desktop, IDE, or MCP?
2. Should Lite store query history by default or make it opt-in?
3. How aggressive should default Lite warnings be?
4. Which providers and models should be supported first?
5. Should Enterprise proxy all model traffic or support advisory-only deployment first?
6. What minimum dashboard set is needed for an initial enterprise release?
7. Which data retention defaults are appropriate for raw and redacted prompts?

---

## 21. Initial Naming Model

- Product family: **PromptShield**
- Local edition: **PromptShield Lite**
- Centralized edition: **PromptShield Enterprise**

This structure should remain flexible if the platform later introduces more editions or managed hosted offerings.
