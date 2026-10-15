"""Pytest configuration and fixtures for SentinelFlow."""

import pytest
from sentinelflow.mcp_tools import PUBLISHED_ARTICLES


@pytest.fixture(autouse=True)
def reset_published_articles():
    """Clear published articles list before each test."""
    PUBLISHED_ARTICLES.clear()
    yield
    PUBLISHED_ARTICLES.clear()
