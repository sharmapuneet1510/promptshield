"""
Message service - formats governance messages from templates.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MessageService:
    """
    Formats human-readable governance messages from configuration templates.

    Templates use Python str.format() syntax with named placeholders.
    """

    def __init__(self, templates: dict[str, str]) -> None:
        self._templates = templates

    def format(self, key: str, **kwargs: Any) -> str:
        """
        Format a message template by key.

        Args:
            key:    Template key (e.g. 'oversized_prompt').
            kwargs: Interpolation values.

        Returns:
            Formatted message string, or a generic fallback.
        """
        template = self._templates.get(key, "")
        if not template:
            return f"Policy rule triggered: {key}"
        try:
            return template.format(**kwargs)
        except (KeyError, ValueError) as e:
            logger.debug("Message template format error for key '%s': %s", key, e)
            return template

    def format_many(self, keys_with_kwargs: list[tuple[str, dict[str, Any]]]) -> list[str]:
        """
        Format multiple messages at once.

        Args:
            keys_with_kwargs: List of (key, kwargs) tuples.

        Returns:
            List of formatted message strings.
        """
        return [self.format(key, **kwargs) for key, kwargs in keys_with_kwargs]
