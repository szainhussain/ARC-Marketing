"""Deterministic, code-level checks run on every agent output after schema
validation. These are cheap, auditable, and can't be talked out of by a
model, unlike asking the QA agent to notice the same thing. Results are
stored on the AgentExecution and failures are passed to Marketing Ops
(agent 11) as confirmed issues."""

import json
import re

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"\+?\d[\d\s().-]{8,}\d")
_HANDLE = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{3,}")


def _split_phrases(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[\n,;]", raw) if len(p.strip()) >= 3]


def _check_prohibited(text: str, profile: dict) -> dict:
    lowered = text.lower()
    hits = [p for p in _split_phrases(profile.get("prohibited_phrases")) if p.lower() in lowered]
    return {
        "check": "prohibited_phrases_absent",
        "passed": not hits,
        "detail": f"Contains prohibited phrase(s): {', '.join(hits)}" if hits else None,
    }


def _check_contacts(text: str) -> dict:
    found = []
    if _EMAIL.search(text):
        found.append("email address")
    if _PHONE.search(text):
        found.append("phone number")
    if _HANDLE.search(text):
        found.append("social handle")
    return {
        "check": "no_contact_details",
        "passed": not found,
        "detail": f"Output contains a {', '.join(found)}, agents must not invent contacts."
        if found
        else None,
    }


def evaluate_output(checks: tuple[str, ...], output: dict, profile: dict) -> list[dict]:
    text = json.dumps(output, ensure_ascii=False)
    results = []
    for check in checks:
        if check == "schema_valid":
            # Reaching this point means the provider adapter's schema.load passed.
            results.append({"check": check, "passed": True, "detail": None})
        elif check == "prohibited_phrases_absent":
            results.append(_check_prohibited(text, profile))
        elif check == "no_contact_details":
            results.append(_check_contacts(text))
    return results
