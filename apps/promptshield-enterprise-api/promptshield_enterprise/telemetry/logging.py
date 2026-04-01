"""
Structured logging configuration using structlog.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", is_production: bool = False) -> None:
    """
    Configure structlog for structured logging.

    In production: JSON output (machine-readable).
    In development: pretty colorized console output.

    Args:
        log_level:     Log level string (DEBUG, INFO, WARNING, ERROR).
        is_production: True for JSON output, False for pretty output.
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
    )

    # Shared processors for all environments
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if is_production:
        # JSON output for production
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Pretty colorized output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Return a bound structlog logger.

    Args:
        name: Logger name (typically __name__).

    Returns:
        A structlog BoundLogger instance.
    """
    return structlog.get_logger(name)
