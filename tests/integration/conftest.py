"""Shared fixtures for integration tests."""
import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested."""
    if not config.getoption("-m") or "integration" not in config.getoption("-m"):
        skip_integration = pytest.mark.skip(reason="need -m integration to run")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
