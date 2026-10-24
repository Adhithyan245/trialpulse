"""Pytest configuration for TrialPulse tests.

Prevents real network calls to Google Gemini API during testing.
"""

import pytest


@pytest.fixture(autouse=True)
def disable_gemini_network(monkeypatch):
    """Make any attempt to construct a real google.genai.Client fail loudly.
    
    Tests that need a client pass their own fake client, so they won't be
    affected by this fixture.
    """
    import google.genai
    
    original_client = google.genai.Client
    
    def raise_on_construct(*args, **kwargs):
        raise RuntimeError("network disabled in tests")
    
    monkeypatch.setattr(google.genai, "Client", raise_on_construct)
