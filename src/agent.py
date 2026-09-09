"""Structured Output Agent - schema-valid JSON from an LLM, every time.

The model is asked for JSON. Models being models, sometimes you get a code
fence, a friendly preamble, or a field that breaks the schema. This module
turns that into a validated Pydantic object or a clearly-marked partial one -
never a surprise.
"""
from __future__ import annotations

import json
import re
from typing import Type, TypeVar

from pydantic import BaseModel, Field, ValidationError

from .llm import complete
from .logging_setup import log

T = TypeVar("T", bound=BaseModel)

MAX_ATTEMPTS = 3
DEMO = "Login button does nothing on mobile Safari, checkout is blocked, several users affected."


class Ticket(BaseModel):
    """The output contract. Replace with whatever shape your app needs."""

    title: str = Field(min_length=3)
    priority: str = Field(pattern="^(low|medium|high|critical)$")
    tags: list[str] = Field(default_factory=list)
    estimate_hours: float = Field(ge=0, le=200)
    confidence: float = 1.0


SYSTEM = (
    "You extract structured data. Reply with ONE JSON object and nothing else - "
    "no markdown fences, no commentary.\n\nJSON Schema:\n{schema}"
)

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def coerce_json(raw: str) -> str:
    """Pull the JSON object out of whatever the model actually sent.

    Handles code fences and leading/trailing prose. Raises ValueError when
    there is no object in there at all.
    """
    fenced = _FENCE.search(raw)
    if fenced:
        raw = fenced.group(1)

    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"no JSON object in model output: {raw[:120]!r}")
    return raw[start : end + 1]


def _partial(schema: Type[T], raw: str) -> T:
    """Best-effort object built from whatever parsed, flagged confidence=0.

    Uses model_construct, which skips validation on purpose: the caller asked
    for a soft failure and gets one they can detect.
    """
    data: dict = {}
    try:
        parsed = json.loads(coerce_json(raw))
        if isinstance(parsed, dict):
            data = {k: v for k, v in parsed.items() if k in schema.model_fields}
    except Exception:  # noqa: BLE001 - a partial is the whole point here
        pass
    data["confidence"] = 0.0
    return schema.model_construct(**data)


def extract(text: str, schema: Type[T] = Ticket, *, strict: bool = True,
            max_attempts: int = MAX_ATTEMPTS) -> T:
    """Return a validated `schema` instance, repairing invalid output as needed.

    Each failure is fed back to the model with the exact validation error, which
    is what makes the second attempt succeed rather than repeat the mistake.
    """
    messages = [
        {"role": "system", "content": SYSTEM.format(schema=json.dumps(schema.model_json_schema()))},
        {"role": "user", "content": text},
    ]
    raw = ""

    for attempt in range(1, max_attempts + 1):
        raw = complete(messages)
        try:
            obj = schema.model_validate_json(coerce_json(raw))
            log.info("validated", extra={"attempt": attempt, "schema": schema.__name__})
            return obj
        except (ValidationError, ValueError) as err:
            log.warning(
                "validation_failed",
                extra={"attempt": attempt, "error": str(err)[:300], "raw": raw[:300]},
            )
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"That failed validation:\n{err}\n\nReturn corrected JSON only.",
            })

    if strict:
        raise RuntimeError(f"no valid {schema.__name__} after {max_attempts} attempts")

    log.error("soft_fail", extra={"schema": schema.__name__})
    return _partial(schema, raw)


def run(prompt: str) -> str:
    return extract(prompt).model_dump_json(indent=2)
