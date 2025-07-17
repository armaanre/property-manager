# parser_llm.py

import json
import openai
import os
from typing import Dict
from rule_parser import EmailParser as RuleBasedParser
from validator import validate_email_data
from jsonschema import ValidationError
from dotenv import load_dotenv
import logging
from dataclasses import asdict

logger = logging.getLogger(__name__)
load_dotenv()

openai.api_key = os.environ.get("OPEN_AI_KEY")
class LLMEmailParser:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self.system_prompt = (
    "You are an assistant that reads a tenant's email and returns ONLY a JSON object "
    "with these fields:\n"
    "  • tenant_name (string)\n"
    "  • address (string or null)\n"
    "  • request_type (one of maintenance, payment, lease, general)\n"
    "  • summary (first line of the tenant's ask)\n"
    "  • full_body (full email text)\n\n"
    "When deciding request_type (based **solely** on the **body**):\n"
    "  1. If the tenant explicitly *withholds* payment until a repair/maintenance issue is fixed → \"maintenance\"\n"
    "  2. Else if they ask about rent, balances, due dates, etc. → \"payment\"\n"
    "  3. Else if they ask about lease terms → \"lease\"\n"
    "  4. Else if they ask about repairs, maintenance, or facility issues → \"maintenance\"\n"
    "  5. Otherwise → \"general\"\n"
    "Respond with *only* valid JSON—nothing else."
        )
        
        self.rule_parser = RuleBasedParser()


    def llm_parse(self, msg: Dict[str, str]) -> Dict[str, str]:
        user_prompt = (
            f"Email headers:\n"
            f"From: {msg['sender']}\n"
            f"Subject: {msg['subject']}\n\n"
            f"Body:\n{msg['body']}\n\n"
            "Return only the JSON."
        )

        resp = openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            temperature=0
        )
        return json.loads(resp.choices[0].message.content)
    
    def parse(self, msg: Dict[str, str]) -> Dict[str, str]:
        try:
            parsed = self.llm_parse(msg)
            validate_email_data(parsed)
            parsed["request_type"] = self.normalize_request_type(parsed)

            return parsed

        except (json.JSONDecodeError, ValidationError, KeyError) as e:
            logger.warning(
                "LLM parsing failed (falling back to rule-based): %s", e
            )

        # Fallback: use rule-based parser 
        return asdict(self.rule_parser.parse(msg))
    
    def normalize_request_type(self, parsed: Dict[str, str]) -> str:
        body = parsed["full_body"].lower()

        # Case A: withholding payment until repair
        withholding_phrases = [
            "not going to send",
            "won't send",
            "will not send",
            "until fix",
            "until you fix"
        ]
        maintenance_keywords = ["fix", "toilet", "leak", "repair", "maintenance"]

        if any(phrase in body for phrase in withholding_phrases) \
           and any(kw in body for kw in maintenance_keywords):
            return "maintenance"

        # Case B: pure payment question
        if any(kw in body for kw in ("rent", "balance", "due", "invoice")):
            return "payment"

        # Case C: lease terms
        if any(kw in body for kw in ("lease", "renew", "agreement")):
            return "lease"

        # Case D: generic maintenance
        if any(kw in body for kw in ("repair", "leak", "clog", "lock", "heat", "ac", "electric")):
            return "maintenance"

        return parsed["request_type"]
    
    
