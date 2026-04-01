"""
Prompt hashing utilities.
"""

from __future__ import annotations

import hashlib


def hash_prompt(text: str) -> str:
    """
    Compute a SHA-256 hex digest of the prompt text.

    Used for deduplication detection and audit trails without storing
    the raw prompt content.

    Args:
        text: The prompt text to hash.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hash_prompt_short(text: str, length: int = 16) -> str:
    """
    Return a shortened SHA-256 hex digest suitable for display purposes.

    Args:
        text:   The prompt text to hash.
        length: Number of hex characters to return (default: 16).

    Returns:
        Truncated hex digest.
    """
    return hash_prompt(text)[:length]
