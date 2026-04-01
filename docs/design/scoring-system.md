# User Effectiveness and Misuse Scoring — Design Reference

## Goals

The scoring system has two primary objectives:

1. **Surface productivity vs. waste.** Give platform teams a quantitative signal for whether AI tooling investment is generating value. The Effectiveness Score answers: "Is this user doing high-value work with Claude?" The Misuse Score answers: "Is this user burning budget on prompts that shouldn't involve an LLM?"

2. **Identify coaching opportunities.** Raw scores and persona classifications should be actionable. A score alone is not useful; the system is designed so that any score in a concerning range maps to a concrete recommended action (see Thresholds section below).

The system deliberately avoids trying to measure the *quality* of Claude's output or the user's overall job performance. It measures only what is observable from the precheck layer: the nature of prompts submitted, the governance decisions applied, and token/cost patterns.

---

## Effectiveness Score Formula and Weights

The Effectiveness Score is a weighted sum of four normalized ratios, clamped to [0.0, 1.0].

```
effectiveness_score = clamp(
    coding_ratio        * 0.40
  + documentation_ratio * 0.20
  + allow_rate          * 0.25
  + token_efficiency    * 0.15,
  0.0, 1.0
)
```

### Component definitions

**`coding_ratio`** (weight: 0.40)

```
coding_ratio = coding_count / total_requests
```

The single strongest signal of productive AI use in an engineering context. Prompts classified as `coding` include code generation, refactoring, debugging, code review, and test writing. This receives the highest weight because it directly measures the core use case that AI tooling is deployed for.

**`documentation_ratio`** (weight: 0.20)

```
documentation_ratio = documentation_count / total_requests
```

Documentation generation (docstrings, READMEs, API docs, commit messages) is high-value AI work with structured output. It receives a lower weight than coding because it is less central to engineering productivity, but it is clearly productive usage.

**`allow_rate`** (weight: 0.25)

```
allow_rate = allow_count / total_requests
```

A user whose prompts consistently pass policy without warnings or blocks is using the tool in a policy-compliant, well-formed way. This component rewards clean usage and penalizes users who frequently trigger policy friction. It is weighted relatively high because policy compliance is a prerequisite for productive usage.

**`token_efficiency`** (weight: 0.15)

```
avg_tokens = total_input_tokens / total_requests

token_efficiency =
    if avg_tokens < 50:    0.2   # Trivially short prompts — not substantive work
    if avg_tokens < 200:   0.6   # Short but potentially useful
    if avg_tokens < 2000:  1.0   # Ideal range — substantive, not excessive
    if avg_tokens < 5000:  0.7   # Long but may be legitimate (large context)
    else:                  0.3   # Consistently oversized — likely inefficient
```

Token efficiency rewards users who write substantive prompts (not one-liners that should be web searches) while penalizing those who routinely dump enormous amounts of text into every prompt. The ideal range of 200–2000 tokens represents well-formed, substantive engineering prompts.

---

## Misuse Score Formula and Weights

The Misuse Score is a weighted sum of four normalized ratios, clamped to [0.0, 1.0].

```
misuse_score = clamp(
    block_rate         * 0.35
  + search_like_ratio  * 0.30
  + oversized_ratio    * 0.20
  + reroute_web_ratio  * 0.15,
  0.0, 1.0
)
```

### Component definitions

**`block_rate`** (weight: 0.35)

```
block_rate = block_count / total_requests
```

The strongest misuse signal. Being blocked means a prompt violated a policy rule. A single block is not concerning. A consistent pattern of blocks is a clear signal of either intentional policy circumvention or a fundamental misunderstanding of appropriate AI use. This receives the highest weight.

**`search_like_ratio`** (weight: 0.30)

```
search_like_ratio = search_like_count / total_requests
```

Prompts classified as `search_like` are queries for general knowledge, current events, simple factual lookups, or questions that any search engine would answer. Using an expensive LLM for these tasks wastes budget and produces lower-quality results than a web search. This is the second-highest weight because it is a very common form of budget waste.

**`oversized_ratio`** (weight: 0.20)

```
oversized_ratio = oversized_count / total_requests
```

Prompts classified as `oversized` consistently exceed the token threshold where cost-effective usage is possible. Repeatedly submitting huge prompts (e.g., pasting entire codebases) is a sign the user has not learned to work effectively within token constraints. This receives a moderate weight — it is wasteful but not necessarily a policy violation.

**`reroute_web_ratio`** (weight: 0.15)

```
reroute_web_ratio = reroute_web_count / total_requests
```

A softer version of the `search_like_ratio` signal. When the precheck engine recommends web search for a prompt, it means the routing analysis determined a search engine would be more appropriate. Users who ignore this advisory repeatedly are getting routing recommendations that go unheeded. Lowest weight because the advisory nature means it is less severe than a block.

---

## Persona Classification Decision Table

Personas are evaluated in priority order. The first matching rule is applied.

| Priority | Persona              | Condition                                                          |
|----------|----------------------|--------------------------------------------------------------------|
| 1        | `abuser`             | `misuse_score >= 0.50` OR `block_rate >= 0.30`                   |
| 2        | `web_searcher`       | `search_like_ratio >= 0.40` OR `reroute_web_ratio >= 0.30`       |
| 3        | `power_user`         | `effectiveness_score >= 0.65` AND `total_requests >= 100` AND `misuse_score < 0.30` |
| 4        | `productive_coder`   | `effectiveness_score >= 0.65` AND `coding_ratio >= 0.40`         |
| 5        | `occasional_user`    | `total_requests < 20`                                             |
| 6        | `unknown`            | None of the above                                                 |

**Why `abuser` is checked first**: A user could theoretically have a high `effectiveness_score` alongside a high `block_rate` (e.g., they do a lot of coding work but also repeatedly attempt blocked prompts). Misuse indicators take precedence over positive signals for safety reasons.

**Why `web_searcher` precedes `power_user`**: A high-volume user who primarily asks search-like questions should not be rewarded with a `power_user` classification. Volume alone does not indicate productive usage.

**Why `occasional_user` is near the bottom**: An infrequent user with only a few requests could appear to have high scores simply due to small sample size. Labeling them `occasional_user` rather than `productive_coder` avoids overfitting to limited data.

---

## Score Decay Over Time

The current implementation uses cumulative lifetime counts with no explicit time decay. This is intentional for the initial version: total request counts are more statistically stable than recent-only windows, which can produce noisy scores for low-frequency users.

A time-weighted variant is planned for a future release. The proposed approach:

```
weighted_count(metric) = sum over all requests of:
    metric_value(request) * exp(-lambda * days_ago(request))
```

Where `lambda` is a decay constant (e.g., `0.01` for a half-life of ~70 days).

This would allow scores to reflect recent behavior more heavily than historical behavior, enabling users who have improved their prompt practices to see their scores improve over time.

Until this is implemented, scores can be manually reset by deleting and recreating a `UserBehaviorProfile` row, which causes it to be rebuilt from subsequent activity.

---

## Example Calculations

### Example 1: Productive Coder (alice)

| Metric               | Value  |
|----------------------|--------|
| total_requests       | 100    |
| coding_count         | 60     |
| documentation_count  | 20     |
| allow_count          | 90     |
| warn_count           | 8      |
| block_count          | 2      |
| search_like_count    | 8      |
| oversized_count      | 5      |
| reroute_web_count    | 6      |
| total_input_tokens   | 120,000 |

**Effectiveness:**
- coding_ratio = 60/100 = 0.60 → 0.60 × 0.40 = 0.240
- documentation_ratio = 20/100 = 0.20 → 0.20 × 0.20 = 0.040
- allow_rate = 90/100 = 0.90 → 0.90 × 0.25 = 0.225
- avg_tokens = 120000/100 = 1200 → token_efficiency = 1.0 → 1.0 × 0.15 = 0.150
- **effectiveness_score = 0.655**

**Misuse:**
- block_rate = 2/100 = 0.02 → 0.02 × 0.35 = 0.007
- search_like_ratio = 8/100 = 0.08 → 0.08 × 0.30 = 0.024
- oversized_ratio = 5/100 = 0.05 → 0.05 × 0.20 = 0.010
- reroute_web_ratio = 6/100 = 0.06 → 0.06 × 0.15 = 0.009
- **misuse_score = 0.050**

**Persona**: `productive_coder` (effectiveness >= 0.65, coding_ratio >= 0.40)

---

### Example 2: Web Searcher (bob)

| Metric               | Value  |
|----------------------|--------|
| total_requests       | 80     |
| coding_count         | 10     |
| documentation_count  | 5      |
| allow_count          | 60     |
| warn_count           | 15     |
| block_count          | 5      |
| search_like_count    | 40     |
| oversized_count      | 3      |
| reroute_web_count    | 30     |
| total_input_tokens   | 32,000 |

**Effectiveness:**
- coding_ratio = 10/80 = 0.125 → 0.125 × 0.40 = 0.050
- documentation_ratio = 5/80 = 0.0625 → 0.0625 × 0.20 = 0.013
- allow_rate = 60/80 = 0.75 → 0.75 × 0.25 = 0.188
- avg_tokens = 32000/80 = 400 → token_efficiency = 1.0 → 1.0 × 0.15 = 0.150
- **effectiveness_score = 0.401**

**Misuse:**
- block_rate = 5/80 = 0.0625 → 0.0625 × 0.35 = 0.022
- search_like_ratio = 40/80 = 0.50 → 0.50 × 0.30 = 0.150
- oversized_ratio = 3/80 = 0.0375 → 0.0375 × 0.20 = 0.008
- reroute_web_ratio = 30/80 = 0.375 → 0.375 × 0.15 = 0.056
- **misuse_score = 0.236**

**Persona**: `web_searcher` (search_like_ratio = 0.50 >= 0.40, takes priority over effectiveness score)

---

### Example 3: Abuser (carol)

| Metric               | Value  |
|----------------------|--------|
| total_requests       | 50     |
| coding_count         | 5      |
| allow_count          | 20     |
| block_count          | 20     |
| search_like_count    | 15     |
| oversized_count      | 10     |
| reroute_web_count    | 8      |
| total_input_tokens   | 250,000 |

**Misuse:**
- block_rate = 20/50 = 0.40 → 0.40 × 0.35 = 0.140
- search_like_ratio = 15/50 = 0.30 → 0.30 × 0.30 = 0.090
- oversized_ratio = 10/50 = 0.20 → 0.20 × 0.20 = 0.040
- reroute_web_ratio = 8/50 = 0.16 → 0.16 × 0.15 = 0.024
- **misuse_score = 0.294**

Note: block_rate = 0.40 >= 0.30, so `abuser` persona triggers via the block_rate threshold even though misuse_score is only 0.294.

**Persona**: `abuser` (block_rate = 0.40 >= 0.30)

---

### Example 4: Power User (dave)

| Metric               | Value  |
|----------------------|--------|
| total_requests       | 450    |
| coding_count         | 180    |
| documentation_count  | 100    |
| allow_count          | 420    |
| block_count          | 5      |
| search_like_count    | 25     |
| oversized_count      | 15     |
| reroute_web_count    | 20     |
| total_input_tokens   | 630,000 |

**Effectiveness:**
- coding_ratio = 180/450 = 0.40 → 0.40 × 0.40 = 0.160
- documentation_ratio = 100/450 = 0.222 → 0.222 × 0.20 = 0.044
- allow_rate = 420/450 = 0.933 → 0.933 × 0.25 = 0.233
- avg_tokens = 630000/450 = 1400 → token_efficiency = 1.0 → 1.0 × 0.15 = 0.150
- **effectiveness_score = 0.587**

**Misuse:**
- block_rate = 5/450 = 0.011 → 0.011 × 0.35 = 0.004
- All other ratios are low
- **misuse_score = 0.028**

**Persona**: `power_user` — effectiveness_score < 0.65 but total_requests = 450 >= 100 and misuse_score < 0.30... Actually effectiveness is 0.587 which is below 0.65, so `power_user` does not trigger. `productive_coder` does not trigger either (effectiveness < 0.65). `occasional_user` does not apply. This user would be `unknown`.

This edge case illustrates that a high-volume, mostly clean user with a moderately diverse prompt mix does not fit a neat persona. Admins should interpret `unknown` for high-volume users as "productive but not narrowly specialized."

---

## Thresholds and Recommended Actions per Score Range

### Effectiveness Score

| Score Range | Recommended Action                                                            |
|-------------|-------------------------------------------------------------------------------|
| >= 0.75     | No action; recognize as a productive user                                     |
| 0.55–0.74   | Optional: share advanced prompt techniques to improve coding ratio            |
| 0.35–0.54   | Schedule coaching session; review prompt history for patterns                 |
| < 0.35      | Proactive outreach; consider limiting quota until usage improves              |

### Misuse Score

| Score Range | Recommended Action                                                            |
|-------------|-------------------------------------------------------------------------------|
| < 0.20      | No action                                                                     |
| 0.20–0.39   | Monitor; send automated tips if search_like_ratio is the primary driver       |
| 0.40–0.59   | Coaching session; explain policy rules and appropriate use cases              |
| >= 0.60     | Immediate manager notification; quota review; access audit                   |

---

## Limitations and Known Edge Cases

**Cold start problem.** Users with fewer than 20 requests have statistically unreliable scores. The `occasional_user` persona serves as a guard against acting on noisy early data. Do not use scores for users with fewer than 10 requests.

**Classification accuracy.** The `coding`, `search_like`, and `documentation` classifications are produced by heuristic rules and lightweight ML in the precheck engine. Misclassifications do occur, particularly for multi-purpose prompts (e.g., "Explain this code and then search for the latest version of the library"). Misclassified prompts contribute noise to the ratios.

**Search-like prompts in legitimate contexts.** Some legitimate engineering tasks look like search queries to the classifier (e.g., "What is the difference between TCP and UDP?" asked in the context of debugging a network issue). A moderate `search_like_ratio` does not always indicate misuse; context matters.

**Team-level analysis not yet supported.** Profiles include a `team_id` field, but the current API does not aggregate scores by team. Team-level analytics are planned for a future release.

**Score inflation from low block rates.** Users who have never submitted a blocked prompt will have a high `allow_rate`, which boosts their effectiveness score even if their `coding_ratio` is low. This is by design — policy compliance is a positive signal — but it means a pure `allow_rate` maximizer who only submits generic prompts will score moderately well. The `coding_ratio` weight is the counterbalance.

**No negative weighting for WARN decisions.** Currently, WARN decisions only reduce the `allow_rate` component. A future version may add a separate `warn_rate` component with a small negative weight to further penalize repeated policy warnings.
