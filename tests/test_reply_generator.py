# tests/test_reply_generator.py

import types
import pytest

import reply_generator
from reply_generator import ReplyGenerator

# Helper to build a fake OpenAI response
def make_mock_resp(content: str):
    msg = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=msg)
    return types.SimpleNamespace(choices=[choice])

@pytest.fixture(autouse=True)
def disable_real_openai(monkeypatch):
    """Prevent real API calls and ensure API key is set."""
    monkeypatch.setenv("OPEN_AI_KEY", "test-key")
    # Reload module so it picks up test env var
    import importlib
    importlib.reload(reply_generator)
    # Stub api_key assignment
    monkeypatch.setattr(reply_generator.openai, "api_key", "test-key")

def test_generate_returns_trimmed_content(monkeypatch):
    # Prepare a dummy reply with surrounding whitespace
    raw_reply = "\n\n  Hello Tenant,\nWe got your request.\n\nBest,\nTeam  \n"
    mock_resp = make_mock_resp(raw_reply)
    # Stub the OpenAI create call
    called = {}
    def fake_create(*, model, messages, temperature, max_completion_tokens):
        called['model'] = model
        called['messages'] = messages
        called['temperature'] = temperature
        called['max_completion_tokens'] = max_completion_tokens
        return mock_resp

    # Monkeypatch the namespaced endpoint
    monkeypatch.setattr(
        reply_generator.openai.chat.completions,
        "create",
        fake_create
    )

    # Instantiate generator
    gen = ReplyGenerator(model="test-model")

    parsed = {
        "tenant_name": "Jane Doe",
        "address": "123 Elm St Apt 5",
        "request_type": "maintenance",
        "summary": "Sink is leaking",
        "full_body": "My kitchen sink is dripping non-stop."
    }
    context = {
        "rent_balance": "$1,200",
        "lease_end_date": "2025-12-31",
        "maintenance_history": [
            {"date": "2025-01-01", "issue": "Clogged sink", "status": "resolved", "id": "MH-001"}
        ]
    }
    ticket_id = "MH-123"

    # Call generate
    reply = gen.generate(parsed, context, ticket_id)

    # 1. Should strip whitespace
    assert reply == "Hello Tenant,\nWe got your request.\n\nBest,\nTeam"

    # 2. Check model and parameters
    assert called['model'] == "test-model"
    assert called['temperature'] == 0.7
    assert called['max_completion_tokens'] == 500

    # 3. Verify that system prompt is first message
    sys_msg = called['messages'][0]
    assert sys_msg["role"] == "system"
    assert sys_msg["content"].startswith("You are a professional property manager assistant.")

    # 4. Verify user prompt includes key pieces
    user_msg = called['messages'][1]
    content = user_msg["content"]
    # Parsed fields
    assert "Tenant: Jane Doe" in content
    assert "Address: 123 Elm St Apt 5" in content
    assert "Type: maintenance" in content
    assert "Summary: Sink is leaking" in content
    # Ticket ID
    assert "Ticket Id:\nMH-123" in content
    # Full body
    assert "My kitchen sink is dripping non-stop." in content
    # Context
    assert "Rent Balance: $1,200" in content
    assert "Lease Ends: 2025-12-31" in content
    # Maintenance history line
    assert "- 2025-01-01: Clogged sink (resolved, id MH-001)" in content

def test_generate_handles_empty_history(monkeypatch):
    # Test with no maintenance_history entries
    raw_reply = "OK"
    mock_resp = make_mock_resp(raw_reply)
    monkeypatch.setattr(
        reply_generator.openai.chat.completions,
        "create",
        lambda **kwargs: mock_resp
    )

    gen = ReplyGenerator()
    parsed = {
        "tenant_name": "Foo",
        "address": None,
        "request_type": "general",
        "summary": "Hello?",
        "full_body": "Just checking in."
    }
    context = {
        "rent_balance": "$0",
        "lease_end_date": "2026-01-01",
        "maintenance_history": []
    }
    ticket_id = "T-000"
    reply = gen.generate(parsed, context, ticket_id)

    # Should return exactly what the LLM provides
    assert reply == "OK"

    # And building the prompt should not crash even with empty history
    # (no exceptions thrown)
    # You can optionally verify that no "- " lines are added:
    reply_generator.openai.chat.completions.create.__wrapped__.keywords['messages'][1]['content'] \
                  if hasattr(reply_generator.openai.chat.completions.create, "__wrapped__") \
                  else None
    # We won't assert on wrapped; just ensure no exception above.
