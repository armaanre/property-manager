# tests/test_parser_llm.py

import json
import pytest
from dataclasses import dataclass, asdict
from jsonschema import ValidationError
import types

import parser
from parser import LLMEmailParser

# A dummy dataclass that mimics the real ParsedEmail
@dataclass
class DummyParsedEmail:
    uid: str = "DUMMY_UID"
    tenant_name: str = "Fallback User"
    address: str = None
    request_type: str = "general"
    summary: str = "fallback summary"
    full_body: str = "fallback body"
    subject: str = "fallback subject"
    date: str = "2025-01-01"

@pytest.fixture(autouse=True)
def disable_real_openai(monkeypatch):
    """Prevent any real OpenAI network calls."""
    monkeypatch.setattr(parser.openai, "api_key", "TEST_KEY")

def make_mock_resp(content: str):
    """Helper to build a fake OpenAI response object."""
    msg = types.SimpleNamespace(content=content)
    choice = types.SimpleNamespace(message=msg)
    return types.SimpleNamespace(choices=[choice])

def test_llm_parse_success(monkeypatch):
    # Given a well-formed JSON response from the LLM
    llm_output = {
        "tenant_name": "Alice",
        "address": "123 Main St Apt 4B",
        "request_type": "payment",
        "summary": "When is rent due?",
        "full_body": "Hi, when is the next rent payment due?"
    }
    mock_resp = make_mock_resp(json.dumps(llm_output))
    monkeypatch.setattr(
        parser.openai.chat.completions, "create",
        lambda **kwargs: mock_resp
    )
    # And validation does not raise
    monkeypatch.setattr(parser, "validate_email_data", lambda data: None)

    parser_llm = LLMEmailParser(model="test-model")
    parsed = parser_llm.llm_parse({
        "sender": "Alice <alice@example.com>",
        "subject": "Rent question",
        "body": "Hi, when is the next rent payment due?"
    })

    assert parsed == llm_output

def test_parse_success_with_normalization(monkeypatch):
    # LLM returns a payment question but body indicates maintenance
    llm_output = {
        "tenant_name": "Bob",
        "address": "200 Elm St Apt 2C",
        "request_type": "payment",  # initial label
        "summary": "I need you to fix the sink",
        "full_body": "I have the rent ready but won't pay until you fix the sink."
    }
    mock_resp = make_mock_resp(json.dumps(llm_output))
    monkeypatch.setattr(
        parser.openai.chat.completions, "create",
        lambda **kwargs: mock_resp
    )
    monkeypatch.setattr(parser, "validate_email_data", lambda data: None)

    parser_llm = LLMEmailParser()
    parsed = parser_llm.parse({
        "sender": "Bob <bob@example.com>",
        "subject": "Maintenance hold",
        "body": llm_output["full_body"]
    })

    # normalize_request_type should override to "maintenance"
    assert parsed["request_type"] == "maintenance"
    assert parsed["tenant_name"] == "Bob"
    assert parsed["address"] == "200 Elm St Apt 2C"

def test_parse_fallback_on_json_error(monkeypatch):
    # LLM returns invalid JSON
    mock_resp = make_mock_resp("NOT A JSON")
    monkeypatch.setattr(
        parser.openai.chat.completions, "create",
        lambda **kwargs: mock_resp
    )
    monkeypatch.setattr(parser, "validate_email_data", lambda data: None)
    # Stub out rule-based parser
    dummy = DummyParsedEmail()
    monkeypatch.setattr(
        parser.RuleBasedParser, "parse",
        lambda self, msg: dummy
    )

    parser_llm = LLMEmailParser()
    result = parser_llm.parse({
        "sender": "Fallback <fb@example.com>",
        "subject": "Any",
        "body": "irrelevant"
    })

    # Should be the asdict of our dummy dataclass
    assert result == asdict(dummy)

def test_parse_fallback_on_validation_error(monkeypatch):
    # LLM returns well-formed JSON that fails schema validation
    llm_output = {
        "tenant_name": "Chloe",
        "address": "300 Oak St Apt 1A",
        # missing request_type field
        "summary": "Hello",
        "full_body": "Just saying hi"
    }
    mock_resp = make_mock_resp(json.dumps(llm_output))
    monkeypatch.setattr(
        parser.openai.chat.completions, "create",
        lambda **kwargs: mock_resp
    )
    # validator raises
    monkeypatch.setattr(
        parser, "validate_email_data",
        lambda data: (_ for _ in ()).throw(ValidationError("fail"))
    )
    # Stub rule-based parser again
    dummy = DummyParsedEmail(tenant_name="Rule", address="X")
    monkeypatch.setattr(
        parser.RuleBasedParser, "parse",
        lambda self, msg: dummy
    )

    parser_llm = LLMEmailParser()
    result = parser_llm.parse({
        "sender": "Rule <rule@example.com>",
        "subject": "Test",
        "body": "irrelevant"
    })

    assert result == asdict(dummy)

@pytest.mark.parametrize("body,expected", [
    # withholding until repair
    ("I won't send rent until you fix the toilet", "maintenance"),
    # pure payment question
    ("What is my rent balance?", "payment"),
    # lease terms
    ("Can I renew my lease?", "lease"),
    # generic maintenance
    ("My heater is broken", "maintenance"),
    # default general
    ("Just hello", "general"),
])
def test_normalize_request_type(body, expected):
    parser_llm = LLMEmailParser()
    parsed = {
        "full_body": body.lower(),
        "request_type": "general"
    }
    assert parser_llm.normalize_request_type(parsed) == expected
