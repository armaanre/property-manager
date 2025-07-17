# reply_generator.py

import openai
from typing import Dict
from dotenv import load_dotenv
import os
load_dotenv()

openai.api_key = os.environ.get("OPEN_AI_KEY")

class ReplyGenerator:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.system_prompt = (
            "You are a professional property manager assistant. "
            "Given a tenant's parsed request, context (account balances, lease dates, maintenance history) and the ticket id raised for the request, "
            "draft a polite, clear, and concise email response. "
            "Always:\n"
            "  • Greet the tenant by their name.\n"
            "  • Acknowledge their specific ask (from summary).\n"
            "  • Reference any relevant context (e.g., rent balance, lease end date, past tickets).\n"
            "  • Explain next steps (e.g., we will schedule maintenance, or here is how to pay due rent).\n"
            "  • State that a ticket with ticket id has been raised for their reference.\n"
            "  • Sign off with Domos Property Management Team.\n"
            "Respond *only* with the email body (no extra JSON or markup)."
        )

    def generate(self, parsed: Dict[str, str], context: Dict[str, any], ticket_id: str) -> str:
        """
        :param parsed: Output of EmailParser.parse(), with keys like
                       tenant_name, address, request_type, summary, full_body.
        :param context: Output of ContextLoader.load(), with keys rent_balance,
                        lease_end_date, maintenance_history, etc.
        :return: The drafted reply as a plain string.
        """
        # Build a structured user prompt that includes both parsed fields and context.
        user_prompt = f"""
Parsed Request:
  Tenant: {parsed['tenant_name']}
  Address: {parsed['address']}
  Type: {parsed['request_type']}
  Summary: {parsed['summary']}

Ticket Id:
{ticket_id}

Full Message:
{parsed['full_body']}

Context:
  Rent Balance: {context['rent_balance']}
  Lease Ends: {context['lease_end_date']}
  Maintenance History:
"""

        for ticket in context["maintenance_history"]:
            user_prompt += (
                f"    - {ticket['date']}: {ticket['issue']} "
                f"({ticket['status']}, id {ticket['id']})\n"
            )

        user_prompt += "\nDraft a response email using this information."

        resp = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system",  "content": self.system_prompt},
                {"role": "user",    "content": user_prompt},
            ],
            temperature=0.7,
            max_completion_tokens=500,
        )

        return resp.choices[0].message.content.strip()
