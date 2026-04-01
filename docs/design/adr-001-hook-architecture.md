# ADR-001: UserPromptSubmit Hook as Governance Intercept Layer

**Status**: Accepted

**Date**: 2026-04-01

**Deciders**: PromptShield platform team

---

## Context

PromptShield needs to intercept user prompts before they reach an LLM provider. The interception must:

1. **Be invisible to the user** during normal operation — no extra confirmation dialogs, no mode switches, no change to the user's workflow.
2. **Run before the prompt reaches Claude** — analysis after the fact cannot block or modify a request.
3. **Work without user configuration** after initial setup — the organization deploying PromptShield should not need end users to do anything except install the tool.
4. **Support blocking** — the mechanism must be able to prevent a prompt from reaching the model entirely.
5. **Support context injection** — for warn and advisory decisions, the mechanism must be able to inject additional context into the conversation without the user having to do anything.
6. **Work across all Claude Code surfaces** — CLI, desktop app, and IDE extension.

Several architectural options were evaluated. This record documents the decision and the reasoning behind it.

---

## Decision

Use Claude Code's `UserPromptSubmit` lifecycle hook as the primary governance intercept layer.

The hook is a shell script registered in `~/.claude/settings.json` under the `hooks.UserPromptSubmit` key. Claude Code fires this hook for every prompt the user submits, before the prompt is sent to the model. The hook script receives the full prompt text as JSON on stdin and can respond with one of three outcomes:

- **Exit 0, no output**: prompt proceeds unchanged (ALLOW)
- **Exit 0, JSON with `hookSpecificOutput.additionalContext`**: prompt proceeds with injected context (WARN, REROUTE_*)
- **Exit 0, JSON with `decision: "block"`**: prompt is stopped; reason is shown to user (BLOCK)

The hook script (`promptshield-check.sh`) is installed once into `~/.claude/hooks/` and registered in `settings.json`. After that, it runs automatically on every prompt with no user action required.

---

## Consequences

### Positive

**Zero end-user friction.** After the one-time installation, the user's workflow is completely unchanged. They type prompts and press Enter. The hook runs in the background. For ALLOW decisions (the majority), the user sees nothing at all. Only WARN and BLOCK decisions surface information to the user.

**Works across all Claude Code interfaces.** The `UserPromptSubmit` hook fires in the CLI, the desktop application, and all IDE extensions that use the Claude Code runtime. A single settings.json change covers all surfaces simultaneously.

**Runs before the model sees the prompt.** This is the only mechanism that can genuinely prevent a prompt from reaching Claude. Post-hoc interception (e.g., via an output handler or API proxy) cannot unring the bell — the model has already received and processed the prompt.

**Supports the full decision spectrum.** The hook protocol natively supports blocking (via `decision: "block"`), context injection (via `additionalContext`), and silent pass-through (via exit 0 with no output). This maps directly to PromptShield's BLOCK, WARN/REROUTE, and ALLOW decisions.

**Declarative, version-controlled configuration.** The hook registration lives in `settings.json`, which can be deployed via MDM, dotfiles management, or a company-wide onboarding script. No Claude Code restart is required when the settings file changes.

**Fallback-safe.** If the hook script fails (binary not found, network timeout), the script exits 0 silently, allowing the prompt through. This means a PromptShield outage never blocks engineers from doing their work.

**Upgradeable in place.** The same hook script handles both Lite (local CLI) and Enterprise (remote API) modes. Upgrading an organization from Lite to Enterprise requires only setting two environment variables — no changes to the hook script or settings.json.

### Negative

**Requires Claude Code.** The hook mechanism is specific to Claude Code. Users accessing Claude via other tools (the web UI, direct API calls, other IDEs without Claude Code) are not governed. PromptShield governance is not universal across all AI access paths.

**Shell script surface.** The hook is a bash script, which introduces a dependency on bash, jq, and curl being available in the execution environment. On some managed enterprise systems, these may not be present or may have version constraints. The script includes path resolution fallbacks to mitigate this.

**No return value from the model.** The hook fires before the model responds. There is no hook that fires after the model responds (at least in the current Claude Code version), which means PromptShield cannot analyze model outputs for policy violations in the response path.

**Latency budget.** The hook runs synchronously in the prompt submission path. If PromptShield analysis takes more than ~1 second, users will notice a delay. The local CLI is fast enough (< 200ms) for most cases, but Enterprise API calls over high-latency networks could be noticeable. The script uses a 5-second curl timeout with fallback to local CLI.

**Single hook per event.** Claude Code currently supports only one hook registration per lifecycle event per settings.json scope. Organizations with existing UserPromptSubmit hooks (e.g., for other tools) may have conflicts to resolve.

---

## Alternatives Considered

### MCP Server (Model Context Protocol)

**What it is.** An MCP server runs as a local process and exposes tools, resources, and prompts to Claude. Claude Code can be configured to connect to one or more MCP servers.

**Why we considered it.** MCP is Claude Code's official extension mechanism. It is more powerful than hooks for context enrichment (MCP servers can dynamically provide rich context) and it has a formal protocol rather than relying on shell scripting.

**Why we did not choose it.** MCP servers cannot block prompts. An MCP server is invoked by Claude *after* it has decided to use a tool or resource — it runs in the model's "inner loop," not in the prompt submission path. There is no MCP primitive for "reject this prompt before it reaches the model." For PromptShield's core use case (governance and blocking), MCP is architecturally insufficient.

Additionally, MCP servers require the user to actively invoke tools. The governance use case requires automatic, invisible interception — not optional tools that users can choose not to call.

### HTTP Proxy (Transparent LLM Proxy)

**What it is.** A proxy server deployed between Claude Code and the Anthropic API that inspects and potentially modifies or blocks requests at the HTTP level.

**Why we considered it.** A proxy is the most powerful interception mechanism — it can inspect both requests and responses, handle any LLM provider, and work regardless of the client tool. Several enterprise AI governance products use this approach.

**Why we did not choose it.** The proxy approach has severe operational complexity for the intended deployment model (developer workstations):

- Requires network-level configuration (certificate installation, proxy environment variables, routing rules) on every developer machine.
- Breaks when developers use VPNs, corporate firewalls, or work offline.
- Requires a running proxy service — a centralized point of failure that can block all AI work if it goes down.
- TLS interception requires installing a custom root certificate, which is a significant security and trust concern on personal developer machines.
- Does not work with Claude Code's local model modes (if/when those exist).

The proxy approach is appropriate for server-side AI deployments where all traffic passes through controlled infrastructure. For developer workstation governance, the operational cost is too high.

### Shell Alias or Wrapper Script

**What it is.** Replace the `claude` binary in PATH with a shell function or wrapper script that intercepts the invocation, runs a precheck, and then conditionally calls the real `claude` binary.

**Why we considered it.** Simple to implement; requires no Claude Code extension points; works regardless of Claude Code version.

**Why we did not choose it.** A shell alias or wrapper cannot inject context into an already-running Claude Code session. It can only intercept at the CLI invocation level, which means it runs once at session start — not on every prompt submitted during an interactive session. Once the user is inside a Claude Code session, subsequent prompts bypass the wrapper entirely.

Additionally, wrapper scripts break on IDE integrations (VS Code, JetBrains, etc.) where Claude Code is launched by the IDE process, not by the user's shell. The hooks mechanism works in all of these environments because it runs inside Claude Code's runtime, not at the process invocation level.

### IDE Extension

**What it is.** A VS Code extension (or equivalent) that intercepts keystrokes or API calls within the IDE.

**Why we considered it.** IDE extensions have access to editor state and can provide rich context about what the user is working on.

**Why we did not choose it.** Building and maintaining separate extensions for VS Code, JetBrains, Neovim, and other editors is a significant ongoing investment. IDE extensions also do not cover the Claude Code CLI, which is a primary usage surface for many engineers. The hooks mechanism provides a single implementation that covers all surfaces.

---

## Why Hooks Win

The `UserPromptSubmit` hook is the only Claude Code extension mechanism that simultaneously:

1. Runs before the model sees the prompt (enabling genuine blocking)
2. Requires no action from the user after initial setup
3. Works across CLI, desktop, and IDE surfaces
4. Supports context injection for non-blocking advisories
5. Can be deployed via organization-managed dotfiles with zero per-user configuration

No other available mechanism satisfies all five criteria. The hook mechanism was designed exactly for this use case — it is the right tool for this job.

---

## References

- [Claude Code Hooks Documentation](https://docs.anthropic.com/en/docs/claude-code/hooks)
- [PromptShield Hook Integration Guide](../integration/claude-code-hook.md)
- [Enterprise Behavioral Analytics](../integration/enterprise-analytics.md)
