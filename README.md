# Aether Guard

**Aether Guard** is an open-source, production-grade **LLM governance and query gateway** that sits in front of one or more AI providers and performs:

- pre-query token estimation
- cost estimation
- prompt classification
- policy enforcement
- intelligent routing
- configurable warning/exception messaging
- query logging and behavior analytics

It is designed for teams and enterprises that want a lightweight, scalable, and transparent control layer for AI usage.

---

## Why Aether Guard

Most organizations are moving toward agentic workflows, AI-powered coding, prompt-driven operations, and model-backed developer tooling. That brings a new class of problems:

- blind LLM usage without pre-query cost awareness
- expensive models used for generic or search-like prompts
- lack of governance over prompt size and usage patterns
- no central place to route requests intelligently
- no analytics to identify inefficient usage or training needs

Aether Guard solves that by acting as a **policy-driven AI gateway**.

---

## Core Capabilities

### 1. Pre-Query Intelligence
Before a prompt reaches a model, Aether Guard can:

- estimate input and output tokens
- estimate likely cost
- classify the prompt
- validate against policy
- return a structured decision

### 2. Policy-Driven Control
Aether Guard can:

- allow requests
- warn users
- block oversized or expensive prompts
- reroute prompts to cheaper models
- reroute generic prompts to web search

### 3. Intelligent Routing
Supported routing decisions include:

- premium coding model
- cheaper model
- local model
- web search
- block
- require confirmation

### 4. Query Governance & Analytics
Aether Guard tracks:

- who is using the system inefficiently
- repeated misuse patterns
- repeated blocked requests
- duplicate or wasteful prompts
- user-level coaching opportunities

### 5. Enterprise Readiness
Aether Guard is designed for:

- FastAPI-based deployment
- Docker and Kubernetes
- Redis-backed counters and rate limiting
- PostgreSQL-backed audit and analytics storage
- OpenTelemetry / Prometheus observability

---

## Example Use Cases

- Prevent expensive coding models from being used like search engines
- Warn users before a large, high-cost request is sent
- Reroute search-like queries to web search
- Enforce per-user or per-team quota policies
- Generate end-of-day reports on inefficient AI usage
- Act as a governance layer for Cloud Code, IDE tooling, MCP servers, or internal AI platforms

---

## High-Level Architecture

```text
Client / IDE / Cloud Code / MCP / UI
                |
                v
        Aether Guard API Gateway
                |
   -----------------------------------
   |         |         |             |
   v         v         v             v
Policy   Estimator   Router      Observability
Engine    Engine      Engine        Engine
   |         |         |             |
   -----------------------------------
                |
                v
      Provider Adapters / Connectors
    OpenAI / Anthropic / Ollama / etc
                |
                v
         Response + Usage Logging