"""Fixtures for Hearth Conversation tests."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock

import pytest

COMPONENT_DIR = Path(__file__).parent.parent / "custom_components" / "hearth_conversation"


def _load_component_module(name: str) -> ModuleType:
    """Load a module directly from the component directory, skipping __init__.py."""
    full_name = f"custom_components.hearth_conversation.{name}"
    if full_name in sys.modules:
        return sys.modules[full_name]
    spec = importlib.util.spec_from_file_location(full_name, COMPONENT_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
    return module


# Pre-load modules that have no HA dependencies
_const = _load_component_module("const")
_api = _load_component_module("api")
