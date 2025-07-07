"""Root conftest.py for Tributum test suite.

This file contains project-wide fixtures and pytest configuration.
"""

import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests that test individual components in isolation"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests that test multiple components"
    )
