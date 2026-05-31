"""Independent runner placeholder for Bollinger Evolver."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from bollinger_evolver.config_loader import load_bollinger_config


def load_runner_config(config_path: str | Path) -> Dict[str, Any]:
    """Load config for future runner orchestration."""

    return load_bollinger_config(config_path)
