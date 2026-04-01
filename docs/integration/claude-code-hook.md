# Integrating PromptShield Lite with Claude Code (Zero-Friction, Automatic)

## Overview

PromptShield integrates with Claude Code via the `UserPromptSubmit` lifecycle hook — a built-in extension point that Claude Code fires before any prompt reaches the model. Once installed, the integration is completely invisible to the user during normal operation: clean prompts flow through silently, while problematic prompts are either enriched with context, redirected, or blocked outright.

There is no pop-up, no sidebar, and no extra confirmation step. The user types a prompt and presses Enter. PromptShield runs in milliseconds in the background. Claude receives the prompt (or does not) based on policy.

This document covers everything needed to deploy and operate the integration.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Claude Code                              │
│                                                                 │
│  User types prompt                                              │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────┐    fires     ┌──────────────────────────┐ │
│  │  UserPromptSubmit│─────────────▶  Hook Script             │ │
│  │  event          │              │  ~/.claude/hooks/         │ │
│  └─────────────────┘              │  promptshield-check.sh   │ │
│                                   └──────────┬───────────────┘ │
│                                              │                  │
│                                              ▼                  │
│                                   ┌──────────────────────────┐ │
│                                   │  PromptShield Precheck   │ │
│                                   │                          │ │
│                                   │  Local CLI  OR           │ │
│                                   │  Enterprise API          │ │
│                                   └──────────┬───────────────┘ │
│                                              │                  │
│                                              ▼                  │
│                                   ┌──────────────────────────┐ │
│                         ┌─────────│     Decision              │ │
│                         │         └──────────────────────────┘ │
│                         │                                       │
│          ┌──────────────┼──────────────┐                       │
│          ▼              ▼              ▼                        │
│       ALLOW          WARN /        BLOCK                        │
│    (silent)        REROUTE      (shown to user,                 │
│         │         (context       prompt stopped)                │
│         │         injected)           │                         │
│         ▼              │              ▼                         │
│   Claude receives       │         Prompt never                  │
│   prompt unchanged      │         reaches Claude                │
│                         ▼                                       │
│                  Claude receives                                │
│                  prompt + advisory                              │
│                  context message                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## How It Works Automatically

After the one-time setup described below, no user action is required on subsequent prompts.

1. The user types any prompt in Claude Code (CLI, desktop app, or IDE extension).
2. Claude Code fires the `UserPromptSubmit` hook before sending the prompt to the model.
3. The hook script reads the prompt text from stdin (delivered as JSON by Claude Code).
4. The script runs `promptshield precheck` against the prompt — either via the local CLI or the Enterprise API.
5. PromptShield returns a JSON decision object within milliseconds.
6. The hook script translates the decision into a Claude Code hook response:
   - `ALLOW`: exits with code 0, no output — Claude receives the prompt unchanged.
   - `WARN`: outputs `additionalContext` JSON — Claude receives the prompt plus a warning message prepended to the context.
   - `REROUTE_WEBSEARCH` / `REROUTE_CHEAPER_MODEL`: outputs `additionalContext` JSON — advisory message injected into context.
   - `BLOCK`: outputs `{"decision": "block", "reason": "..."}` — Claude Code stops the prompt and shows the reason to the user.

The entire roundtrip, including classification and policy evaluation, completes in under 200ms for local mode and under 500ms for Enterprise API mode on a typical connection.

---

## Installation

### Prerequisites

- Claude Code installed (CLI or desktop app)
- `uv` package manager
- `jq` command-line JSON processor (used by the hook script)

### Step 1: Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify:

```bash
uv --version
```

### Step 2: Install PromptShield as a uv tool

```bash
uv tool install promptshield-lite
```

Verify:

```bash
promptshield --version
```

If `promptshield` is not on your PATH after install, ensure `~/.local/bin` is in your shell's `PATH`:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

### Step 3: Copy the hook script

```bash
mkdir -p ~/.claude/hooks
cp /path/to/aether-guard/hooks/promptshield-check.sh ~/.claude/hooks/
chmod +x ~/.claude/hooks/promptshield-check.sh
```

### Step 4: Configure Claude Code settings.json

Edit `~/.claude/settings.json` (create it if it does not exist):

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "~/.claude/hooks/promptshield-check.sh"
          }
        ]
      }
    ]
  }
}
```

The empty `matcher` string means the hook fires on every prompt. No restart of Claude Code is required — hook changes take effect immediately.

### Step 5: Verify the installation

Run a test prompt in Claude Code:

```
What is the capital of France?
```

The prompt should go through silently (ALLOW decision). To see the hook output for debugging, run the hook script manually:

```bash
echo '{"prompt": "What is the capital of France?"}' | ~/.claude/hooks/promptshield-check.sh
```

---

## Hook Behavior Reference

| Decision              | User Sees                                   | Claude Receives                          | Hook Exit Code |
|-----------------------|---------------------------------------------|------------------------------------------|---------------|
| `ALLOW`               | Nothing (silent)                            | Original prompt, unchanged               | 0             |
| `WARN`                | Nothing directly; warning in context        | Prompt + warning message in context      | 0             |
| `REROUTE_WEBSEARCH`   | Nothing directly; advisory in context       | Prompt + web search advisory in context  | 0             |
| `REROUTE_CHEAPER_MODEL` | Nothing directly; advisory in context    | Prompt + model routing advisory          | 0             |
| `BLOCK`               | Error message with reason shown by Claude Code | Prompt never reaches Claude           | 0 (block JSON)|

For `WARN` and `REROUTE_*` decisions, the advisory message is injected as `additionalContext` in the hook response. Claude Code prepends this to the conversation context, so Claude is aware of the advisory and can factor it into its response.

For `BLOCK`, the hook returns `{"decision": "block", "reason": "..."}`. Claude Code intercepts this and displays the reason to the user without forwarding the prompt to the model.

---

## Configuration via Environment Variables

The hook script reads the following environment variables at runtime:

| Variable                    | Default                   | Description                                                      |
|-----------------------------|---------------------------|------------------------------------------------------------------|
| `PROMPTSHIELD_MODEL`        | `claude-sonnet-4-6`       | The model name used for token estimation in the precheck engine  |
| `PROMPTSHIELD_USER`         | `$(whoami)`               | The user ID sent with each request for tracking and quotas       |
| `PROMPTSHIELD_ENTERPRISE_URL` | *(unset)*               | If set, route precheck calls to the Enterprise API instead of local CLI |
| `PROMPTSHIELD_ENTERPRISE_API_KEY` | *(unset)*           | API key for authenticating with the Enterprise API               |

Set these in your shell profile (`~/.zshrc` or `~/.bashrc`):

```bash
export PROMPTSHIELD_MODEL="claude-opus-4-5"
export PROMPTSHIELD_USER="alice@company.com"
```

Or for Enterprise mode:

```bash
export PROMPTSHIELD_ENTERPRISE_URL="https://promptshield.internal.company.com"
export PROMPTSHIELD_ENTERPRISE_API_KEY="psk_live_..."
```

---

## Customizing Thresholds

PromptShield Lite uses two configuration files to control behavior:

### `thresholds.yaml`

Located at `~/.config/promptshield/thresholds.yaml` (or the path configured in `PROMPTSHIELD_CONFIG_DIR`).

```yaml
# Token count thresholds
warn_above_tokens: 2000          # Emit WARN if estimated input tokens exceed this
block_above_tokens: 8000         # Emit BLOCK if estimated input tokens exceed this

# Cost thresholds (USD per request)
warn_above_cost_usd: 0.05        # Emit WARN if estimated cost exceeds this
block_above_cost_usd: 0.50       # Emit BLOCK if estimated cost exceeds this

# Misuse score thresholds
warn_above_misuse_score: 0.6     # Emit WARN if misuse score exceeds this
block_above_misuse_score: 0.85   # Emit BLOCK if misuse score exceeds this
```

### `routing.yaml`

Controls when to suggest alternative routing:

```yaml
# Reroute to web search when search-like ratio exceeds this value
reroute_web_search_ratio: 0.7

# Reroute to a cheaper model when the prompt is classified as simple/generic
reroute_cheaper_model_classifications:
  - generic
  - documentation
```

Changes to these files take effect on the next precheck call — no restart required.

---

## Connecting to the Enterprise API

When `PROMPTSHIELD_ENTERPRISE_URL` and `PROMPTSHIELD_ENTERPRISE_API_KEY` are both set, the hook script bypasses the local CLI and instead calls the Enterprise API's `/api/v1/precheck` endpoint via `curl`.

The Enterprise API returns the same JSON structure as the local CLI, so the hook script's decision-handling logic is unchanged. The difference is that Enterprise mode:

- Persists every request to a central PostgreSQL database
- Updates the user's behavioral profile (effectiveness score, misuse score, persona)
- Enforces centrally managed policies and quotas
- Makes the request visible in the Enterprise dashboard and analytics API

### Fallback behavior

If the Enterprise API call fails (network error, timeout, non-200 response), the hook script falls back to the local CLI automatically. If neither is available, the hook exits silently with code 0, allowing the prompt to proceed.

This ensures that a PromptShield outage never blocks users from using Claude Code.

---

## Upgrading from Lite to Enterprise

The upgrade path is intentionally zero-friction:

1. Deploy the Enterprise API (see Enterprise deployment guide).
2. Set the two environment variables in your shell profile:

```bash
export PROMPTSHIELD_ENTERPRISE_URL="https://your-enterprise-host"
export PROMPTSHIELD_ENTERPRISE_API_KEY="your-admin-key"
```

3. Reload your shell: `source ~/.zshrc`

The same hook script handles both modes. No other changes are needed. Local SQLite data from Lite mode is not migrated automatically — it remains accessible via `promptshield history` for reference.

---

## Troubleshooting

### Hook is not firing

- Verify `settings.json` is valid JSON: `cat ~/.claude/settings.json | jq .`
- Verify the hook script is executable: `ls -la ~/.claude/hooks/promptshield-check.sh`
- Check Claude Code version supports hooks (requires Claude Code 1.x or later).

### `promptshield: command not found`

- Verify installation: `uv tool list | grep promptshield`
- Ensure `~/.local/bin` is in PATH: `echo $PATH`
- Try the absolute path: `~/.local/bin/promptshield --version`

### All prompts are being blocked

- Run the hook manually to see the decision: `echo '{"prompt": "your prompt here"}' | ~/.claude/hooks/promptshield-check.sh`
- Check `thresholds.yaml` — your `block_above_tokens` or `block_above_misuse_score` may be too low.
- Check `~/.config/promptshield/policies.yaml` for overly restrictive rules.

### Enterprise API calls failing

- Verify the URL is reachable: `curl -s "$PROMPTSHIELD_ENTERPRISE_URL/health"`
- Verify the API key is correct: `curl -H "X-API-Key: $PROMPTSHIELD_ENTERPRISE_API_KEY" "$PROMPTSHIELD_ENTERPRISE_URL/api/v1/analytics/summary"`
- The hook will fall back to local CLI if Enterprise is unreachable — check hook output for `[PromptShield] Enterprise call failed` log lines.

### Hook is slow

- Enterprise API latency: check network path and server load.
- Local CLI cold start: `uv run` adds ~100ms on first call. Switch to the installed tool: `uv tool install promptshield-lite`.

---

*For Enterprise API reference, see [enterprise-analytics.md](enterprise-analytics.md).*
