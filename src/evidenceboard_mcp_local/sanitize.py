from __future__ import annotations

import re


PATTERNS = [
    (re.compile(r"<\s*/?\s*system\s*>", flags=re.IGNORECASE), "system-tag"),
    (re.compile(r"ignore previous instructions", flags=re.IGNORECASE), "instruction-override"),
    (re.compile(r"do not call tools", flags=re.IGNORECASE), "tool-suppression"),
    (re.compile(r"change priorities", flags=re.IGNORECASE), "priority-manipulation"),
]


def sanitize_note(text: str) -> tuple[str, list[str]]:
    findings: list[str] = []
    sanitized = text
    for pattern, label in PATTERNS:
        if pattern.search(sanitized):
            findings.append(label)
            sanitized = pattern.sub("[sanitized]", sanitized)
    sanitized = sanitized.replace("`", "'").replace("{", "(").replace("}", ")")
    return sanitized, findings
