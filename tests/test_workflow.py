# tests/test_workflow.py
import json
import pytest
from datetime import datetime, timezone

import workflow
from workflow import WorkflowTrigger

@pytest.fixture(autouse=True)
def fix_id_and_time(monkeypatch):
    # 1. Stub out nanoid.generate → fixed ID
    monkeypatch.setattr(workflow, "generate", lambda alphabet, size: "TESTID1234")
    # 2. Create a fixed datetime instance
    fixed_dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    # 3. Replace workflow.datetime with a dummy that returns fixed_dt
    class DummyDateTime:
        @staticmethod
        def now(tz):
            # ignore tz passed in; always return our fixed datetime
            return fixed_dt
    monkeypatch.setattr(workflow, "datetime", DummyDateTime)
    # workflow.timezone is still the real timezone class
    yield

def make_sample_parsed():
    return {
        "tenant_name": "Alice",
        "address": "101 Test St Apt 5",
        "subject": "Leaky faucet",
        "summary": "The kitchen faucet is leaking",
        "request_type": "maintenance"
    }

def make_sample_context():
    return {
        "rent_balance": "$1,234",
        "lease_end_date": "2025-12-31",
        "maintenance_history": [
            {"date": "2024-06-01", "issue": "Clogged sink", "status": "resolved"},
            {"date": "2024-07-15", "issue": "Broken heater", "status": "in_progress"}
        ],
        "property_manager": "Bob Manager"
    }

def test_create_action_item_structure():
    parsed  = make_sample_parsed()
    context = make_sample_context()

    trigger = WorkflowTrigger(output_dir="test_action_items_directory")
    item = trigger.create_action_item(parsed, context)

    # ID and timestamp are our stubs
    assert item["id"] == "TESTID1234"
    # Note: workflow adds "Z" after isoformat
    expected_ts = datetime(2025,1,1,12,0,0,tzinfo=timezone.utc).isoformat() + "Z"
    assert item["created_at"] == expected_ts

    # action_type based on request_type
    assert item["action_type"] == "maintenance_ticket"
    # Fields copied from parsed
    assert item["tenant_name"] == "Alice"
    assert item["address"] == "101 Test St Apt 5"
    assert item["subject"] == "Leaky faucet"
    assert item["summary"] == "The kitchen faucet is leaking"
    assert item["request_type"] == "maintenance"
    # Context nested correctly
    assert item["context"]["rent_balance"] == "$1,234"
    assert item["context"]["lease_end_date"] == "2025-12-31"
    assert isinstance(item["context"]["maintenance_history"], list)
    # Assignee field
    assert item["asignee"] == "Bob Manager"
    # Default status
    assert item["status"] == "pending"

def test_save_action_item(tmp_path):
    action_item = {
        "id": "FOO123",
        "created_at": "2025-01-02T00:00:00+00:00Z",
        "action_type": "payment_reminder",
        "tenant_name": "X",
        "address": "Y",
        "subject": "S",
        "summary": "M",
        "request_type": "payment",
        "context": {
            "rent_balance": "$0",
            "lease_end_date": "2026-01-01",
            "maintenance_history": []
        },
        "status": "pending",
        "asignee": None
    }

    outdir = tmp_path / "actions"
    trigger = WorkflowTrigger(output_dir=str(outdir))

    path = trigger.save_action_item(action_item)
    # Should have created the file with the ID as its name
    expected_path = outdir / "FOO123.json"
    assert path == str(expected_path)
    saved = json.loads(expected_path.read_text())
    assert saved == action_item

def test_process_end_to_end(tmp_path):
    parsed  = make_sample_parsed()
    context = make_sample_context()

    outdir = tmp_path / "ai"
    trigger = WorkflowTrigger(output_dir=str(outdir))

    returned_id = trigger.process(parsed, context)
    # process() returns the ID, not the path
    assert returned_id == "TESTID1234"

    filepath = outdir / "TESTID1234.json"
    assert filepath.exists()

    content = json.loads(filepath.read_text())
    expected = trigger.create_action_item(parsed, context)
    assert content == expected
