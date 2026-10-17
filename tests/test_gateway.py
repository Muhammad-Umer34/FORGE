"""Unit tests for the gateway's provider choice (D-184). No network: the client is only built."""
import pytest

from agents import gateway


@pytest.fixture
def env(monkeypatch):
    for name in ("LLM_PROVIDER", "VERTEX_API_KEY", "STUDIO_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_vertex_is_used_when_its_key_exists(env):
    env.setenv("VERTEX_API_KEY", "vertex-key")
    env.setenv("STUDIO_API_KEY", "studio-key")
    assert gateway.provider() == "vertex"
    assert gateway.api_key() == "vertex-key"


def test_ai_studio_without_a_vertex_key(env):
    env.setenv("STUDIO_API_KEY", "studio-key")
    assert gateway.provider() == "studio"
    assert gateway.api_key() == "studio-key"


@pytest.mark.parametrize("choice, expected_key", [("studio", "studio-key"), ("VERTEX", "vertex-key")])
def test_llm_provider_setting_wins(env, choice, expected_key):
    env.setenv("VERTEX_API_KEY", "vertex-key")
    env.setenv("STUDIO_API_KEY", "studio-key")
    env.setenv("LLM_PROVIDER", choice)
    assert gateway.api_key() == expected_key


def test_unknown_setting_falls_back_to_the_key_rule(env):
    env.setenv("VERTEX_API_KEY", "vertex-key")
    env.setenv("LLM_PROVIDER", "something-else")
    assert gateway.provider() == "vertex"


@pytest.mark.parametrize("vertex_key, expect_vertex", [("vertex-key", True), (None, False)])
def test_client_is_built_for_the_chosen_provider(env, vertex_key, expect_vertex):
    env.setenv("STUDIO_API_KEY", "studio-key")
    if vertex_key:
        env.setenv("VERTEX_API_KEY", vertex_key)
    client = gateway._llm("gemini-3.1-flash-lite")
    assert client.vertexai is expect_vertex
    assert client.google_api_key.get_secret_value() == (vertex_key or "studio-key")


@pytest.mark.parametrize("variable", ["GEMINI_API_KEY", "GOOGLE_API_KEY"])
def test_vertex_refuses_a_key_the_sdk_would_pick_up_instead(env, variable):
    env.setenv("VERTEX_API_KEY", "vertex-key")
    env.setenv(variable, "old-studio-key")
    with pytest.raises(gateway.ModelCallError, match="STUDIO_API_KEY"):
        gateway._llm("gemini-3.1-flash-lite")


def test_vertex_client_uses_the_vertex_key(env):
    env.setenv("VERTEX_API_KEY", "vertex-key")
    client = gateway._llm("gemini-3.1-flash-lite")
    assert client.client._api_client.vertexai is True
    assert client.client._api_client.api_key == "vertex-key"  # what the SDK really sends
