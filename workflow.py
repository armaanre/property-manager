# workflow.py

import os
import json
from nanoid import generate
from datetime import datetime, timezone
from typing import Dict, Any

class WorkflowTrigger:
    """
    Generate back-of-house action items from parsed tenant requests
    and persist them as JSON files on disk.
    """
    _ACTION_MAP = {
        "maintenance": "maintenance_ticket",
        "payment":     "payment_reminder",
        "lease":       "lease_info_request",
        "general":     "general_inquiry"
    }

    def __init__(self, output_dir: str = "action_items"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def create_action_item(
        self,
        parsed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        req_type = parsed.get("request_type", "general")
        action_type = self._ACTION_MAP.get(req_type, "general_inquiry")

        return {
            "id":    generate('1234567890abcdef', 10),
            "created_at":   datetime.now(timezone.utc).isoformat() + "Z",
            "action_type":  action_type,
            "tenant_name":  parsed.get("tenant_name"),
            "address":    parsed.get("address"),
            "subject":      parsed.get("subject"),
            "summary":      parsed.get("summary"),
            "request_type": req_type,
            "context": {
                "rent_balance":       context.get("rent_balance"),
                "lease_end_date":     context.get("lease_end_date"),
                "maintenance_history": context.get("maintenance_history"),
            },
            "status": "pending",
            "asignee": context.get("property_manager")
        }

    def save_action_item(self, action_item: Dict[str, Any]) -> str:
        """
        Write the action_item dict as a JSON file.
        Returns the filepath.
        """
        filename = f"{action_item['id']}.json"
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(action_item, f, indent=2)
        return path

    def process(
        self,
        parsed: Dict[str, Any],
        context: Dict[str, Any]
    ) -> str:
        """
        End-to-end: create + save an action item, returning its filepath.
        """
        item = self.create_action_item(parsed, context)
        self.save_action_item(item)
        return item['id']
