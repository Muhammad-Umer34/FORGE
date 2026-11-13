"""Unit tests for the gateway's provider choice (D-184). No network: the client is only built."""
import pytest

from agents import gateway


@pytest.fixture
def env(monkeypatch):
    for name in ("LLM_PROVIDER", "VERTEX_API_KEY", "STUDIO_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENROUTER_API_KEY"):
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


# ---------------------------------------------------------------- cost and budget (D-216)
def test_cost_uses_the_price_table_and_prices_unknown_models_high():
    assert gateway.cost_of("gemini-2.5-pro", 1_000_000, 100_000) == pytest.approx(1.25 + 1.00)
    assert gateway.cost_of("gemini-3.8-flash", 2_000, 1_000) == pytest.approx((2_000 * 0.75 + 1_000 * 3.75) / 1e6)
    assert gateway.cost_of("some-new-model", 1_000_000, 0) == gateway.cost_of("gemini-2.5-pro", 1_000_000, 0)


class _Reply:
    usage_metadata = {"input_tokens": 10_000, "output_tokens": 2_000}


class _FakeLLM:
    def with_structured_output(self, schema, include_raw):
        return self

    def invoke(self, messages):
        return {"raw": _Reply(), "parsed": "ok", "parsing_error": None}


def test_each_call_adds_its_cost(monkeypatch):
    monkeypatch.setattr(gateway, "_llm", lambda model: _FakeLLM())
    monkeypatch.setattr(gateway, "model_for", lambda task: "gemini-2.5-pro")
    result, usage = gateway.call_structured("planning", object, "s", "u", budget_usd=0.5)
    assert result == "ok" and usage.cost_usd == pytest.approx((10_000 * 1.25 + 2_000 * 10.0) / 1e6)


@pytest.mark.parametrize("budget", [0.0, -0.01])
def test_no_call_is_made_once_the_budget_is_spent(monkeypatch, budget):
    monkeypatch.setattr(gateway, "_llm", lambda model: pytest.fail("the model must not be called"))
    with pytest.raises(gateway.BudgetExceededError):
        gateway.call_structured("planning", object, "s", "u", budget_usd=budget)


def test_budget_left_is_the_cap_minus_what_the_run_spent():
    from datetime import datetime, timezone
    from agents.state import RequestInfo, UsageSummary, budget_left, initial_state
    state = initial_state(RequestInfo(request_id="r", user_id="u", project_id="p", prompt="x",
                                      created_at=datetime.now(timezone.utc)))
    assert budget_left(state) == state["run_config"].limits.max_run_cost_usd
    state["usage"] = UsageSummary(estimated_cost_usd=0.4)
    assert budget_left(state) == pytest.approx(state["run_config"].limits.max_run_cost_usd - 0.4)


# ---------------------------------------------------------------- tracing (D-215)
def test_tracing_is_off_without_keys(monkeypatch):
    from agents import tracing
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    assert tracing.run_config("req_1") == {"configurable": {"thread_id": "req_1"}}


def test_tracing_groups_a_run_under_its_request(monkeypatch):
    from agents import tracing
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setenv("LANGFUSE_TRACING_ENABLED", "false")      # build the handler, send nothing
    config = tracing.run_config("req_1", ("eval",))
    assert config["configurable"] == {"thread_id": "req_1"}
    assert len(config["callbacks"]) == 1
    assert config["metadata"] == {"langfuse_session_id": "req_1", "langfuse_tags": ["eval"]}


# ---------------------------------------------------------------- OpenRouter (D-218) and parallel clients
def test_openrouter_client_uses_its_key_and_address(env):
    env.setenv("VERTEX_API_KEY", "vertex-key")
    env.setenv("OPENROUTER_API_KEY", "or-key")
    env.setenv("LLM_PROVIDER", "openrouter")
    client = gateway._llm("xiaomi/mimo-v2.6-pro")
    assert gateway.api_key() == "or-key"
    assert client.model_name == "xiaomi/mimo-v2.6-pro"
    assert client.openai_api_base == gateway.OPENROUTER_URL
    assert client.openai_api_key.get_secret_value() == "or-key"


def test_vertex_clients_can_be_built_in_parallel(env):
    """The Google SDK sets GOOGLE_API_KEY for a moment while building a Vertex client; the first parallel eval run
    failed 71 of 72 runs because another thread's check saw it."""
    from concurrent.futures import ThreadPoolExecutor
    env.setenv("VERTEX_API_KEY", "vertex-key")
    with ThreadPoolExecutor(8) as pool:
        clients = list(pool.map(lambda _: gateway._llm("gemini-3.8-flash"), range(40)))
    assert len(clients) == 40

