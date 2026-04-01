# Enterprise Behavioral Analytics and User Scoring

## Overview

The Enterprise API tracks every prompt that passes through PromptShield and builds a rolling behavioral profile for each user. These profiles power two composite scores — an **Effectiveness Score** and a **Misuse Score** — and classify each user into one of five **personas** that describe how they are actually using AI tooling at your organization.

The goal is not surveillance. It is productivity intelligence: giving engineering managers and platform teams the data they need to answer questions like:

- Which engineers are using Claude most productively for coding work?
- Which users are spending budget on prompts that should be web searches?
- Who is hitting policy blocks repeatedly and may need coaching or access review?
- Is our Claude rollout delivering measurable productivity value?

Analytics data is available via REST API (described below) and visualized in the Enterprise dashboard.

---

## Data Model

Every precheck request creates a `PromptRecord` row. The Enterprise API also maintains a `UserBehaviorProfile` row per user, updated after each request.

### PromptRecord fields

| Field               | Type      | Description                                                        |
|---------------------|-----------|--------------------------------------------------------------------|
| `id`                | UUID      | Unique record identifier                                           |
| `request_id`        | UUID      | Client-supplied request correlation ID                             |
| `user_id`           | string    | Identifier of the user who submitted the prompt                    |
| `team_id`           | string    | Optional team or department identifier                             |
| `source`            | string    | Source tag (e.g., `claude-code`, `api`, `vscode`)                 |
| `model`             | string    | Target model name                                                  |
| `input_tokens`      | integer   | Estimated input token count                                        |
| `output_tokens`     | integer   | Estimated output token count                                       |
| `total_tokens`      | integer   | Sum of input and output tokens                                     |
| `cost_usd`          | float     | Estimated cost in USD for this request                             |
| `decision`          | string    | Governance decision: `ALLOW`, `WARN`, `BLOCK`, `REROUTE_WEBSEARCH`, `REROUTE_CHEAPER_MODEL` |
| `classifications`   | string[]  | Semantic labels: `coding`, `documentation`, `search_like`, `oversized`, `generic` |
| `misuse_score`      | float     | Per-request misuse signal (0.0–1.0)                               |
| `prompt_hash`       | string    | SHA-256 hash of the prompt (for deduplication, never the raw text) |
| `redacted_prompt`   | string    | First 200 chars with PII tokens replaced                           |
| `raw_prompt`        | string    | Full prompt text (only if `STORE_RAW_PROMPTS=true`)               |
| `route_taken`       | string    | Actual routing decision: `primary`, `web_search`, `cheaper_model` |
| `created_at`        | timestamp | UTC timestamp of the request                                       |

### UserBehaviorProfile fields

| Field                  | Type      | Description                                                        |
|------------------------|-----------|--------------------------------------------------------------------|
| `user_id`              | string    | Primary key; matches `PromptRecord.user_id`                       |
| `team_id`              | string    | Most recent team_id seen for this user                             |
| `total_requests`       | integer   | Cumulative request count                                           |
| `allow_count`          | integer   | Requests that received an ALLOW decision                           |
| `warn_count`           | integer   | Requests that received a WARN decision                             |
| `block_count`          | integer   | Requests that received a BLOCK decision                            |
| `reroute_web_count`    | integer   | Requests routed to web search                                      |
| `reroute_cheaper_count`| integer   | Requests routed to a cheaper model                                 |
| `total_input_tokens`   | integer   | Cumulative input tokens across all requests                        |
| `total_output_tokens`  | integer   | Cumulative output tokens across all requests                       |
| `total_cost_usd`       | float     | Cumulative cost in USD                                             |
| `coding_count`         | integer   | Requests classified as `coding`                                    |
| `documentation_count`  | integer   | Requests classified as `documentation`                             |
| `search_like_count`    | integer   | Requests classified as `search_like`                               |
| `oversized_count`      | integer   | Requests classified as `oversized`                                 |
| `generic_count`        | integer   | Requests classified as `generic`                                   |
| `effectiveness_score`  | float     | Computed effectiveness score (0.0–1.0)                            |
| `misuse_score`         | float     | Computed misuse score (0.0–1.0)                                   |
| `persona`              | string    | Classified persona label                                           |
| `first_seen`           | timestamp | UTC timestamp of user's first request                              |
| `last_seen`            | timestamp | UTC timestamp of user's most recent request                        |
| `updated_at`           | timestamp | UTC timestamp of last profile update                               |

---

## The Effectiveness Score (0.0–1.0)

The Effectiveness Score measures how well a user is leveraging AI for high-value, productive work. A score of 1.0 means every prompt is well-formed, policy-compliant, and directed at tasks where AI provides clear value. A score of 0.0 means prompts are mostly unproductive or wasteful.

### How it is computed

```
effectiveness_score =
    (coding_ratio        * 0.40)
  + (documentation_ratio * 0.20)
  + (allow_rate          * 0.25)
  + (token_efficiency    * 0.15)
```

Where:

- `coding_ratio` = `coding_count / total_requests` — fraction of prompts classified as coding work
- `documentation_ratio` = `documentation_count / total_requests` — fraction classified as structured documentation generation
- `allow_rate` = `allow_count / total_requests` — fraction that passed policy without modification or block
- `token_efficiency` = score based on average tokens per request being in a productive range (neither trivially small nor excessively large); peaks at ~500–2000 tokens per request

The score is clamped to [0.0, 1.0].

### Interpreting the score

| Range      | Interpretation                                                              |
|------------|-----------------------------------------------------------------------------|
| 0.75–1.0   | Highly productive; user is leveraging AI effectively for substantive work   |
| 0.55–0.74  | Productive with room to improve; some non-coding or policy-flagged prompts  |
| 0.35–0.54  | Mixed usage; significant fraction of prompts are not high-value AI work     |
| 0.0–0.34   | Low effectiveness; mostly search-like, generic, or policy-blocked prompts   |

---

## The Misuse Score (0.0–1.0)

The Misuse Score measures signals of unproductive or policy-violating behavior. A score of 0.0 means clean usage with no policy friction. A score of 1.0 means repeated blocks, heavy search-engine misuse, and oversized prompt submissions.

### How it is computed

```
misuse_score =
    (block_rate         * 0.35)
  + (search_like_ratio  * 0.30)
  + (oversized_ratio    * 0.20)
  + (reroute_web_ratio  * 0.15)
```

Where:

- `block_rate` = `block_count / total_requests`
- `search_like_ratio` = `search_like_count / total_requests`
- `oversized_ratio` = `oversized_count / total_requests`
- `reroute_web_ratio` = `reroute_web_count / total_requests`

The score is clamped to [0.0, 1.0].

### Interpreting the score

| Range      | Interpretation                                                              |
|------------|-----------------------------------------------------------------------------|
| 0.0–0.19   | Clean usage; no significant misuse signals                                  |
| 0.20–0.39  | Low misuse; occasional search-like or oversized prompts                     |
| 0.40–0.59  | Moderate misuse; user may benefit from guidance on prompt best practices    |
| 0.60–1.0   | High misuse; review recommended; consider coaching or access adjustment     |

---

## User Persona Classification

After scores are computed, each user is assigned a persona. Personas are determined by a priority-ordered decision tree applied to the scores and raw ratios.

| Persona              | Primary Signals                                              | Recommended Action                                           |
|----------------------|--------------------------------------------------------------|--------------------------------------------------------------|
| `productive_coder`   | effectiveness >= 0.65 AND coding_ratio >= 0.40              | Celebrate; potential power user                              |
| `power_user`         | effectiveness >= 0.65 AND total_requests >= 100 AND misuse < 0.30 | High-volume productive user; candidate for expanded quotas |
| `web_searcher`       | search_like_ratio >= 0.40 OR reroute_web_ratio >= 0.30      | Coach on when to use web search vs. AI; review routing rules |
| `abuser`             | misuse >= 0.50 OR block_rate >= 0.30                        | Immediate review; consider quota reduction or access controls|
| `occasional_user`    | total_requests < 20                                          | Onboarding support; low-touch engagement                     |
| `unknown`            | Does not fit the above categories                            | Monitor; no action required yet                              |

Personas are re-evaluated on every request. A user's persona can move up (e.g., from `occasional_user` to `productive_coder`) or down (e.g., from `productive_coder` to `web_searcher`) as their behavior changes.

---

## API Endpoints for Analytics

All analytics endpoints require the admin API key in the `X-API-Key` header.

### List all user profiles

```
GET /api/v1/analytics/profiles
```

Query parameters:
- `min_requests` (integer, default: 1) — exclude users with fewer than this many requests

Returns an array of `UserBehaviorProfile` objects.

### Get a single user's profile

```
GET /api/v1/analytics/profiles/{user_id}
```

Returns a single `UserBehaviorProfile` object, or 404 if the user has no recorded activity.

### Get profiles by persona

```
GET /api/v1/analytics/profiles/persona/{persona}
```

Valid persona values: `productive_coder`, `power_user`, `web_searcher`, `abuser`, `occasional_user`, `unknown`

Returns an array of `UserBehaviorProfile` objects with the specified persona.

### Effectiveness leaderboard

```
GET /api/v1/analytics/leaderboard
```

Query parameters:
- `metric` (string, default: `effectiveness_score`) — one of `effectiveness_score`, `misuse_score`, `total_requests`
- `limit` (integer, default: 20) — number of users to return

Returns top users sorted by the requested metric descending.

### Abuse report

```
GET /api/v1/analytics/abuse
```

Query parameters:
- `threshold` (float, default: 0.5) — minimum misuse score to include

Returns users whose misuse score exceeds the threshold.

---

## Example API Responses

### `GET /api/v1/analytics/profiles/alice@company.com`

```json
{
  "user_id": "alice@company.com",
  "team_id": "platform-engineering",
  "total_requests": 347,
  "allow_count": 312,
  "warn_count": 28,
  "block_count": 7,
  "reroute_web_count": 14,
  "reroute_cheaper_count": 5,
  "total_input_tokens": 523400,
  "total_output_tokens": 198700,
  "total_cost_usd": 12.47,
  "coding_count": 198,
  "documentation_count": 76,
  "search_like_count": 42,
  "oversized_count": 12,
  "generic_count": 19,
  "effectiveness_score": 0.74,
  "misuse_score": 0.18,
  "persona": "productive_coder",
  "first_seen": "2026-01-15T09:23:11Z",
  "last_seen": "2026-04-01T14:05:33Z",
  "updated_at": "2026-04-01T14:05:33Z"
}
```

### `GET /api/v1/analytics/leaderboard?metric=effectiveness_score&limit=3`

```json
[
  {
    "rank": 1,
    "user_id": "alice@company.com",
    "team_id": "platform-engineering",
    "effectiveness_score": 0.74,
    "misuse_score": 0.18,
    "total_requests": 347,
    "persona": "productive_coder"
  },
  {
    "rank": 2,
    "user_id": "bob@company.com",
    "team_id": "backend",
    "effectiveness_score": 0.71,
    "misuse_score": 0.12,
    "total_requests": 512,
    "persona": "power_user"
  },
  {
    "rank": 3,
    "user_id": "carol@company.com",
    "team_id": "platform-engineering",
    "effectiveness_score": 0.68,
    "misuse_score": 0.09,
    "total_requests": 201,
    "persona": "productive_coder"
  }
]
```

### `GET /api/v1/analytics/profiles/persona/abuser`

```json
[
  {
    "user_id": "dave@company.com",
    "team_id": "marketing",
    "total_requests": 89,
    "block_count": 31,
    "effectiveness_score": 0.21,
    "misuse_score": 0.67,
    "persona": "abuser",
    "last_seen": "2026-03-31T16:42:00Z"
  }
]
```

---

## Using Analytics to Coach Users

### Identifying coaching opportunities

1. **`web_searcher` persona**: Schedule a 15-minute session to demonstrate when Claude adds value versus a web search (real-time data, proprietary context, creative tasks). Share the routing advisory messages the user has been receiving.

2. **High `oversized_ratio`**: The user is likely pasting large files or documents into prompts. Coach them on using file attachment features, breaking work into smaller tasks, or using the `@file` reference syntax.

3. **High `block_rate`**: Review the redacted prompt samples for this user in the requests log. Common causes: policy keywords, excessive token counts, restricted topics. Share the policy documentation and examples of compliant prompts.

4. **Low `coding_ratio` for engineers**: The user may not know how to use Claude for coding tasks effectively. Run a workshop on prompt patterns for code review, refactoring, test generation, and documentation.

### Automated coaching triggers

The analytics API supports building automated coaching workflows. For example:

- Query `GET /api/v1/analytics/profiles/persona/web_searcher` weekly and trigger a Slack message with a prompt tips guide.
- Query `GET /api/v1/analytics/abuse?threshold=0.5` and create a Jira ticket for the user's manager to review.
- Query `GET /api/v1/analytics/leaderboard?metric=effectiveness_score` monthly and recognize top users in an internal newsletter.

---

## Privacy Considerations

### What is stored

- **Always stored**: token counts, costs, decision type, classification labels, misuse score, request metadata.
- **Stored by default (redacted)**: First 200 characters of the prompt with PII patterns replaced by `[REDACTED]`.
- **Stored only if opted in**: Full raw prompt text (`STORE_RAW_PROMPTS=true` environment variable). Not recommended for production unless required for compliance purposes.

### What is never stored

- API keys, passwords, or secrets detected in prompts (these trigger a BLOCK decision before storage).
- Personally identifiable information in the raw prompt (when `STORE_RAW_PROMPTS=false`).

### Data retention

Configure retention in the Enterprise API settings. The default is 90 days for prompt records and 365 days for user behavior profiles. Profiles are updated in-place (not versioned), so historical score trajectories are not stored — only current scores.

### Access control

- All analytics endpoints require the admin API key.
- User profile data should be treated as sensitive HR-adjacent data.
- Consider restricting analytics access to engineering leadership and designated platform administrators.

---

*For the scoring system design reference, see [../design/scoring-system.md](../design/scoring-system.md).*
*For the hook architecture decision, see [../design/adr-001-hook-architecture.md](../design/adr-001-hook-architecture.md).*
