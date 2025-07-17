# parser.py

import re
from dataclasses import dataclass
from email.utils import parseaddr
from typing import Optional, Dict

@dataclass
class ParsedEmail:
    uid: str
    tenant_name: str
    address: Optional[str]
    request_type: str
    subject: str
    date: str
    summary: str
    full_body: str

class EmailParser:
    def __init__(self):
        # Precompile regexes and keyword sets once
        self._apt_regex = re.compile(r'(?:Apartment|Apt|Unit)\s*#?\s*(\w+)', re.IGNORECASE)
        self._kw = {
            "maintenance": {
                "leak", "repair", "broken", "clog", "lock", "heat", "ac", "electric"
            },
            "payment": {
                "rent", "balance", "pay", "payment", "late fee", "invoice"
            },
            "lease": {
                "lease", "renew", "term", "agreement", "extend"
            }
        }

    def parse(self, msg: Dict[str, str]) -> ParsedEmail:
        """
        Turn a raw message dict into a ParsedEmail.
        """
        tenant_name = self._parse_name(msg["sender"])
        address   = self._parse_address(msg["body"])
        request_type= self._classify_request(msg["body"])
        summary     = self._extract_summary(msg["body"])

        return ParsedEmail(
            uid         = msg["uid"],
            tenant_name = tenant_name,
            address   = address,
            request_type= request_type,
            subject     = msg.get("subject", ""),
            date        = msg.get("date", ""),
            summary     = summary,
            full_body   = msg.get("body", "")
        )

    def _parse_name(self, raw_from: str) -> str:
        """
        Extract display name or fallback to local-part of email.
        """
        name, email_addr = parseaddr(raw_from)
        return name or email_addr.split("@")[0]

    def _parse_address(self, body: str) -> Optional[str]:
        """
        Look for "Apartment/Unit #X" patterns in the body.
        """
        m = self._apt_regex.search(body)
        return m.group(1) if m else None

    def _classify_request(self, body: str) -> str:
        """
        Determine request type by scanning for keywords.
        Defaults to 'general' if no category keywords match.
        """
        text = body.lower()
        for category, kws in self._kw.items():
            if any(kw in text for kw in kws):
                return category
        return "general"

    def _extract_summary(self, body: str) -> str:
        """
        Return the first non-blank line of the body as the summary.
        """
        for line in body.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""
