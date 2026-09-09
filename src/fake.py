"""Canned replies so the project runs with MODEL=fake.

Deliberately gets it wrong the first time, so you can watch the repair loop work.
"""
from __future__ import annotations

_calls = {"n": 0}

BROKEN = """Sure! Here's the ticket:

```json
{"title": "Login button broken on mobile Safari",
 "priority": "urgent",
 "tags": ["mobile", "checkout"],
 "estimate_hours": 3}
```"""

FIXED = """{"title": "Login button broken on mobile Safari",
 "priority": "critical",
 "tags": ["mobile", "checkout", "safari"],
 "estimate_hours": 3}"""


def reset() -> None:
    _calls["n"] = 0


def respond(messages: list[dict]) -> str:
    _calls["n"] += 1
    return BROKEN if _calls["n"] == 1 else FIXED
