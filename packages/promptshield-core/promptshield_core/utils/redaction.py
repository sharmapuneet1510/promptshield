"""
Prompt redaction utilities.

Used to produce safe, truncated representations of prompts for logging
and audit storage without exposing sensitive content.
"""

from __future__ import annotations

_REDACTION_SUFFIX = "... [redacted]"


def redact_prompt(text: str, max_chars: int = 200) -> str:
    """
    Truncate a prompt to at most *max_chars* characters and append a
    redaction marker if truncation occurred.

    Args:
        text:      The prompt text to redact.
        max_chars: Maximum number of characters to retain (default: 200).

    Returns:
        The (possibly truncated) prompt text.
    """
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars].rstrip()
    return truncated + _REDACTION_SUFFIX


def redact_pii(text: str) -> str:
    """
    Apply basic PII redaction patterns to prompt text.

    Currently redacts:
    - Email addresses
    - Phone numbers (simple patterns)

    This is a best-effort function and should not be relied upon as a
    comprehensive PII scrubber.

    Args:
        text: The prompt text to process.

    Returns:
        Text with detected PII replaced by placeholders.
    """
    import re

    # Email addresses
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[EMAIL]",
        text,
    )

    # Simple phone numbers (US-style and international)
    text = re.sub(
        r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[PHONE]",
        text,
    )

    return text
