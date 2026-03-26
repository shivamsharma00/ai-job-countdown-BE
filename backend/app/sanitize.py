"""Input sanitization to prevent prompt injection in free-text fields."""

import re

# Patterns that indicate prompt injection attempts
_INJECTION_RE = re.compile(
    r"ignore\s+previous"
    r"|system\s*:"
    r"|\[INST\]"
    r"|<\|"
    r"|</s>"
    r"|###"
    r"|`{3,}",
    re.IGNORECASE,
)

# Control characters (U+0000–U+001F and U+007F)
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")


def sanitize_text(value: str) -> str:
    """Strip control chars, reject injection patterns, return stripped value."""
    value = _CONTROL_RE.sub("", value).strip()
    if _INJECTION_RE.search(value):
        raise ValueError("Input contains disallowed content")
    return value
