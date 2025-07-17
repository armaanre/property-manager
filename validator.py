# validation.py

from jsonschema import validate

EMAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "tenant_name":   {"type": "string", "minLength": 1},
        "address":     {"anyOf": [{"type": "string"}, {"type": "null"}]},
        "request_type":  {"type": "string",
                          "enum": ["maintenance", "payment", "lease", "general"]},
        "summary":       {"type": "string", "minLength": 1},
        "full_body":     {"type": "string", "minLength": 1},
    },
    "required": ["tenant_name", "address", "request_type", "summary", "full_body"],
    "additionalProperties": False
}

def validate_email_data(data: dict) -> None:
    """
    Raises ValidationError if `data` doesn't match EMAIL_SCHEMA.
    """
    validate(instance=data, schema=EMAIL_SCHEMA)
