"""
Configuration loader for PromptShield.

Loads YAML configuration files from the bundled defaults directory and
optionally merges user-provided overrides from a custom config directory.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from promptshield_config.validators import (
    ExceptionsConfig,
    FullConfig,
    ProvidersConfig,
    RoutingConfig,
    ThresholdsConfig,
)

logger = logging.getLogger(__name__)

# Path to the bundled default config files
_DEFAULTS_DIR = Path(__file__).parent / "defaults"

_CONFIG_FILES = {
    "thresholds": "thresholds.yaml",
    "routing": "routing.yaml",
    "exceptions": "exceptions.yaml",
    "providers": "providers.yaml",
}


class ConfigLoader:
    """
    Loads and merges PromptShield configuration.

    Configuration is loaded in the following priority order (highest wins):
    1. Bundled defaults (``promptshield_config/defaults/``)
    2. User config directory (``config_dir``, if provided)

    Deep merge is applied for dict keys; scalar values from the user config
    override defaults.

    Example::

        loader = ConfigLoader(config_dir=Path("~/.config/promptshield"))
        config = loader.load_all()
    """

    def __init__(self, config_dir: Path | None = None) -> None:
        """
        Initialise the loader.

        Args:
            config_dir: Optional path to a user config directory.
                        YAML files in this directory override defaults.
        """
        self._config_dir = Path(config_dir).expanduser() if config_dir else None
        self._cache: dict[str, dict[str, Any]] = {}

    def _load_yaml_file(self, path: Path) -> dict[str, Any]:
        """Load a YAML file and return its contents as a dict."""
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            logger.warning("Failed to parse YAML file %s: %s", path, e)
            return {}

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """
        Deep-merge *override* into *base*, returning a new dict.
        Dict values are merged recursively; all other types are replaced.
        """
        result = dict(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _load_section(self, name: str) -> dict[str, Any]:
        """Load and merge defaults + user override for a config section."""
        if name in self._cache:
            return self._cache[name]

        filename = _CONFIG_FILES[name]

        # Load defaults
        defaults = self._load_yaml_file(_DEFAULTS_DIR / filename)

        # Load user override
        user_data: dict[str, Any] = {}
        if self._config_dir:
            user_path = self._config_dir / filename
            user_data = self._load_yaml_file(user_path)
            if user_data:
                logger.debug("Loaded user config override: %s", user_path)

        merged = self._deep_merge(defaults, user_data)
        self._cache[name] = merged
        return merged

    def load_thresholds(self) -> ThresholdsConfig:
        """Load and validate threshold configuration."""
        data = self._load_section("thresholds")
        return ThresholdsConfig.model_validate(data)

    def load_routing(self) -> RoutingConfig:
        """Load and validate routing configuration."""
        data = self._load_section("routing")
        return RoutingConfig.model_validate(data)

    def load_providers(self) -> ProvidersConfig:
        """Load and validate providers/pricing configuration."""
        data = self._load_section("providers")
        return ProvidersConfig.model_validate(data)

    def load_exceptions(self) -> ExceptionsConfig:
        """Load and validate exception message templates."""
        data = self._load_section("exceptions")
        return ExceptionsConfig.model_validate(data)

    def load_all(self) -> FullConfig:
        """
        Load and validate all config sections, returning a unified FullConfig.

        Returns:
            A FullConfig instance with all sections populated.
        """
        return FullConfig(
            thresholds=self.load_thresholds(),
            routing=self.load_routing(),
            providers=self.load_providers(),
            exceptions=self.load_exceptions(),
        )

    def invalidate_cache(self) -> None:
        """Clear the in-memory config cache, forcing a reload on next access."""
        self._cache.clear()
