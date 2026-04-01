"""
promptshield-core
=================

Shared core library for PromptShield. Contains the precheck engine,
token estimator, classifier, policy engine, misuse detector, and all
shared contracts/schemas.

Both PromptShield Lite and Enterprise import from this package.
"""

from promptshield_core.classifier import classify_prompt
from promptshield_core.contracts.request import PromptRequest
from promptshield_core.contracts.response import PromptDecisionResponse
from promptshield_core.enums import Decision, PromptCategory, RouteTarget
from promptshield_core.exceptions import (
    ConfigurationError,
    PolicyViolationError,
    PromptShieldError,
    ProviderError,
    ValidationError,
)
from promptshield_core.misuse_detector import MisuseDetector, UsageStats, compute_misuse_score
from promptshield_core.policy_engine import PolicyEngine
from promptshield_core.precheck_engine import PreCheckEngine

__version__ = "0.1.0"

__all__ = [
    # Engine
    "PreCheckEngine",
    # Contracts
    "PromptRequest",
    "PromptDecisionResponse",
    # Enums
    "Decision",
    "PromptCategory",
    "RouteTarget",
    # Services
    "classify_prompt",
    "PolicyEngine",
    "MisuseDetector",
    "UsageStats",
    "compute_misuse_score",
    # Exceptions
    "PromptShieldError",
    "ConfigurationError",
    "PolicyViolationError",
    "ValidationError",
    "ProviderError",
    # Version
    "__version__",
]
