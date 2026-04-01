"""
PromptShield core enumerations.

Defines the canonical decision types, prompt categories, and routing targets
used throughout the PromptShield system.
"""

from enum import Enum


class Decision(str, Enum):
    """Final governance decision for a prompt request."""

    ALLOW = "ALLOW"
    """The request is permitted as-is."""

    WARN = "WARN"
    """The request is permitted but the user should be notified of a concern."""

    BLOCK = "BLOCK"
    """The request is blocked and should not be forwarded to the model."""

    REROUTE_WEBSEARCH = "REROUTE_WEBSEARCH"
    """The request looks like a general-knowledge query; suggest web search instead."""

    REROUTE_CHEAPER_MODEL = "REROUTE_CHEAPER_MODEL"
    """The request can be fulfilled by a cheaper model; suggest rerouting."""

    REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
    """The request requires explicit user confirmation before proceeding."""


class PromptCategory(str, Enum):
    """Classification category for a prompt."""

    CODING = "coding"
    """The prompt is about writing, reviewing, or debugging code."""

    DOCUMENTATION = "documentation"
    """The prompt is about documentation, summaries, or explanations."""

    GENERIC = "generic"
    """The prompt is a generic LLM task that doesn't fit other categories."""

    SEARCH_LIKE = "search_like"
    """The prompt resembles a search/general-knowledge query."""

    OVERSIZED = "oversized"
    """The prompt exceeds the configured token threshold."""

    BROAD_SCOPE = "broad_scope"
    """The prompt is vague, very short, or asks for many unrelated things."""

    REPETITIVE = "repetitive"
    """The prompt appears to be a repeated or near-duplicate request."""

    UNKNOWN = "unknown"
    """Category could not be determined."""


class RouteTarget(str, Enum):
    """The routing target suggested or enforced by the decision."""

    REQUESTED_MODEL = "requested_model"
    """Forward to the model originally requested."""

    CHEAPER_MODEL = "cheaper_model"
    """Forward to a cheaper alternative model."""

    LOCAL_MODEL = "local_model"
    """Forward to a local/self-hosted model (e.g. Ollama)."""

    WEB_SEARCH = "web_search"
    """Route to a web-search engine instead of an LLM."""

    BLOCK = "block"
    """Do not route anywhere; the request is blocked."""

    REQUIRE_CONFIRMATION = "require_confirmation"
    """Hold the request pending user confirmation."""
