from __future__ import annotations

from app import mock_llm, mock_rag
from app.incidents import STATE
from scripts import inject_incident, load_test


def test_rag_retrieve_is_wrapped_for_subcomponent_tracing(monkeypatch) -> None:
    assert hasattr(mock_rag.retrieve, "__wrapped__")

    monkeypatch.setitem(STATE, "tool_fail", False)
    monkeypatch.setitem(STATE, "rag_slow", False)

    docs = mock_rag.retrieve.__wrapped__("Explain the refund policy")

    assert docs == ["Refunds are available within 7 days with proof of purchase."]


def test_llm_generate_is_wrapped_as_a_generation(monkeypatch) -> None:
    assert hasattr(mock_llm.FakeLLM.generate, "__wrapped__")

    monkeypatch.setattr(mock_llm.time, "sleep", lambda _: None)
    monkeypatch.setitem(STATE, "cost_spike", False)

    llm = mock_llm.FakeLLM(model="test-model")
    response = mock_llm.FakeLLM.generate.__wrapped__(llm, "Question=What happened?")

    assert response.model == "test-model"
    assert response.usage.input_tokens >= 20
    assert response.usage.output_tokens >= 80


def test_role_e_scripts_allow_a_non_default_api_port(monkeypatch) -> None:
    monkeypatch.setenv("DAY13_BASE_URL", "http://127.0.0.1:8001/")

    assert load_test.get_base_url() == "http://127.0.0.1:8001"
    assert inject_incident.get_base_url() == "http://127.0.0.1:8001"
