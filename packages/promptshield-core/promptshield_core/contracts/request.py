"""
PromptRequest contract - the input schema for all precheck requests.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_config


class PromptRequest(BaseModel):
    """
    Represents a single prompt governance check request.

    This model is the primary input to the PromptShield precheck engine and
    is shared between Lite and Enterprise editions.
    """

    model_config = model_config(
        frozen=False,
        populate_by_name=True,
        str_strip_whitespace=True,
    )

    request_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for this request. Auto-generated if not provided.",
    )
    prompt_text: str = Field(
        ...,
        min_length=1,
        description="The full text of the prompt to be evaluated.",
    )
    model: str = Field(
        ...,
        min_length=1,
        description="The target model identifier (e.g. 'gpt-4o', 'claude-sonnet-4').",
    )
    user_id: str = Field(
        ...,
        min_length=1,
        description="The identifier of the user or service account making the request.",
    )
    team_id: str | None = Field(
        default=None,
        description="Optional team or group identifier for quota grouping.",
    )
    source: str = Field(
        default="unknown",
        description="Source of the request (e.g. 'cli', 'vscode', 'api', 'mcp').",
    )
    project: str | None = Field(
        default=None,
        description="Optional project name for request attribution.",
    )
    repository: str | None = Field(
        default=None,
        description="Optional repository name, useful for IDE/CI integrations.",
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session identifier for conversation-level tracking.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when the request was created.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary key-value metadata attached to the request.",
    )

    @field_validator("prompt_text")
    @classmethod
    def validate_prompt_not_empty(cls, v: str) -> str:
        """Ensure prompt text is not only whitespace."""
        if not v.strip():
            raise ValueError("prompt_text must not be empty or whitespace only")
        return v

    @field_validator("model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Normalize model name to lowercase."""
        return v.lower().strip()
