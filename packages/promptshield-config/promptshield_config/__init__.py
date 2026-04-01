"""
promptshield-config
===================

Configuration loading and validation for PromptShield.
Provides YAML-based config with Pydantic v2 validation and
sensible defaults.
"""

from promptshield_config.loader import ConfigLoader
from promptshield_config.validators import (
    ExceptionsConfig,
    FullConfig,
    ModelPricing,
    ProvidersConfig,
    RoutingConfig,
    ThresholdsConfig,
)

__version__ = "0.1.0"

__all__ = [
    "ConfigLoader",
    "FullConfig",
    "ThresholdsConfig",
    "RoutingConfig",
    "ExceptionsConfig",
    "ModelPricing",
    "ProvidersConfig",
]
