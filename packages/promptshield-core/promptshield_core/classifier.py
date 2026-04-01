"""
Rule-based prompt classifier.

Assigns one or more PromptCategory labels to a prompt based on heuristics.
Designed to be fast, deterministic, and transparent.
"""

from __future__ import annotations

import re

from promptshield_core.enums import PromptCategory

# ---------------------------------------------------------------------------
# Compiled regex patterns
# ---------------------------------------------------------------------------

# Search/general-knowledge patterns - short factual questions
_SEARCH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(what is|what are|what was|what were)\b", re.IGNORECASE),
    re.compile(r"\b(who is|who are|who was|who were)\b", re.IGNORECASE),
    re.compile(r"\b(when did|when was|when is|when are)\b", re.IGNORECASE),
    re.compile(r"\b(where is|where are|where was|where were)\b", re.IGNORECASE),
    re.compile(r"\bhow does .{0,40} work\b", re.IGNORECASE),
    re.compile(r"\btell me about\b", re.IGNORECASE),
    re.compile(r"\bdefine\b.{0,30}\b(term|word|concept|phrase)\b", re.IGNORECASE),
    re.compile(r"\bwhat.{0,10}(capital|president|founder|inventor|ceo)\b", re.IGNORECASE),
]

# Code-related patterns
_CODE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"```", re.IGNORECASE),
    re.compile(r"\b(def |class |import |from .+ import|function |async def )\b"),
    re.compile(r"\b(var |let |const |=>|\.map\(|\.filter\(|\.reduce\()\b"),
    re.compile(r"\b(SELECT |INSERT |UPDATE |DELETE |CREATE TABLE)\b", re.IGNORECASE),
    re.compile(r"\b(bug|fix|debug|refactor|implement|unit test|write a function|write a class)\b", re.IGNORECASE),
    re.compile(r"\b(code review|pull request|merge|git|github|linting|type hint)\b", re.IGNORECASE),
    re.compile(r"<[a-zA-Z][^>]{0,50}>"),  # HTML/XML tags
]

# Documentation patterns
_DOCS_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(write (a )?(doc|documentation|readme|wiki|summary|report))\b", re.IGNORECASE),
    re.compile(r"\b(summarize|summarise)\b", re.IGNORECASE),
    re.compile(r"\b(explain (this|the|my|our) (code|function|class|module|file|script))\b", re.IGNORECASE),
    re.compile(r"\b(document (this|the|my|our))\b", re.IGNORECASE),
    re.compile(r"\b(add (docstrings?|comments?|jsdoc|typedoc))\b", re.IGNORECASE),
    re.compile(r"\b(write (a )?(blog|article|post|essay|email|letter))\b", re.IGNORECASE),
    re.compile(r"\b(translate|paraphrase|rewrite|rephrase)\b", re.IGNORECASE),
]

# Broad scope signals - vague/multi-topic prompts
_BROAD_SCOPE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(everything|anything|all (of|about)|everything about|tell me everything)\b", re.IGNORECASE),
    re.compile(r"\b(and also|as well as|in addition|furthermore|moreover|plus)\b", re.IGNORECASE),
]

# Oversized threshold
_OVERSIZED_TOKEN_THRESHOLD = 8000

# Broad scope short prompt threshold (tokens)
_BROAD_SCOPE_SHORT_THRESHOLD = 20


def classify_prompt(
    prompt_text: str,
    input_tokens: int,
) -> list[PromptCategory]:
    """
    Classify a prompt into one or more PromptCategory values.

    Classification is additive – a prompt may belong to multiple categories.
    The first matching category in the priority list becomes the primary one,
    but all applicable categories are returned.

    Args:
        prompt_text:  The prompt text to classify.
        input_tokens: Pre-computed token count for this prompt.

    Returns:
        Non-empty list of PromptCategory. Falls back to [PromptCategory.UNKNOWN]
        if no rules match.
    """
    categories: list[PromptCategory] = []

    # 1. Oversized check (token-based, highest priority signal)
    if input_tokens >= _OVERSIZED_TOKEN_THRESHOLD:
        categories.append(PromptCategory.OVERSIZED)

    # 2. Broad scope (very short or explicitly multi-topic)
    if input_tokens < _BROAD_SCOPE_SHORT_THRESHOLD:
        categories.append(PromptCategory.BROAD_SCOPE)
    elif _matches_any(prompt_text, _BROAD_SCOPE_PATTERNS) and input_tokens < 80:
        categories.append(PromptCategory.BROAD_SCOPE)

    # 3. Coding
    if _matches_any(prompt_text, _CODE_PATTERNS):
        categories.append(PromptCategory.CODING)

    # 4. Documentation
    if _matches_any(prompt_text, _DOCS_PATTERNS):
        categories.append(PromptCategory.DOCUMENTATION)

    # 5. Search-like (only if not already coding/docs - avoids false positives)
    if PromptCategory.CODING not in categories and PromptCategory.DOCUMENTATION not in categories:
        if _matches_any(prompt_text, _SEARCH_PATTERNS):
            # Extra check: short prompts (< 60 tokens) are more likely search-like
            if input_tokens < 200:
                categories.append(PromptCategory.SEARCH_LIKE)

    # 6. Generic fallback
    if not categories or (len(categories) == 1 and PromptCategory.OVERSIZED in categories):
        if PromptCategory.OVERSIZED not in categories:
            categories.append(PromptCategory.GENERIC)

    # If we only have OVERSIZED and nothing else matched, add GENERIC
    if categories == [PromptCategory.OVERSIZED]:
        categories.append(PromptCategory.GENERIC)

    # Deduplicate preserving order
    seen: set[PromptCategory] = set()
    result = []
    for c in categories:
        if c not in seen:
            seen.add(c)
            result.append(c)

    return result if result else [PromptCategory.UNKNOWN]


def _matches_any(text: str, patterns: list[re.Pattern[str]]) -> bool:
    """Return True if the text matches any of the provided regex patterns."""
    return any(p.search(text) for p in patterns)


def get_primary_category(categories: list[PromptCategory]) -> PromptCategory:
    """
    Return the single most significant category from a classification result.

    Priority order: OVERSIZED > BLOCK > SEARCH_LIKE > CODING > DOCUMENTATION
    > BROAD_SCOPE > REPETITIVE > GENERIC > UNKNOWN
    """
    priority = [
        PromptCategory.OVERSIZED,
        PromptCategory.SEARCH_LIKE,
        PromptCategory.CODING,
        PromptCategory.DOCUMENTATION,
        PromptCategory.BROAD_SCOPE,
        PromptCategory.REPETITIVE,
        PromptCategory.GENERIC,
        PromptCategory.UNKNOWN,
    ]
    for cat in priority:
        if cat in categories:
            return cat
    return PromptCategory.UNKNOWN
