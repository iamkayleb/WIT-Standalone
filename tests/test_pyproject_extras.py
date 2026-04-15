"""Regression tests for workflow-required extras in pyproject.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path


def test_app_extra_exists_for_reusable_ci_workflow() -> None:
    """The reusable CI workflow installs `.[app,dev]`."""
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    extras = pyproject["project"]["optional-dependencies"]

    assert "app" in extras
    assert extras["app"] == extras["langchain"]
