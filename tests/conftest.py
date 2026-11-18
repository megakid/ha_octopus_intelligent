"""Shared fixtures for the Octopus Intelligent tests."""
import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load this repo's custom_components in every test."""
    yield
