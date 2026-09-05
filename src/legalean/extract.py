"""LLM-based extraction of structured Rule objects from statute excerpts.

This is the ONLY module in the project that calls the Anthropic API. Conflict
detection (conflicts.py) never touches the network, so the core logic can be
exercised and verified against data/rules.json without spending API credits.

Requires an Anthropic API key (from console.anthropic.com -- a Claude.ai chat
subscription is separate and does not grant API access) in ANTHROPIC_API_KEY.
Defaults to Claude Opus 5; override with the LEGALEAN_MODEL env var if you'd
rather trade quality for lower cost (e.g. claude-sonnet-5, claude-haiku-4-5).
"""

from __future__ import annotations

import json
import os

import anthropic

from .models import RULE_JSON_SCHEMA, Rule, Statute

DEFAULT_MODEL = os.environ.get("LEGALEAN_MODEL", "claude-opus-5")

SYSTEM_PROMPT = """You are a precise legal-text formalizer. Given one excerpt \
from a statute, extract a single structured rule that captures its core \
logical claim, and return ONLY that rule as JSON matching the provided schema.

Guidance:
- `subject`: who the rule addresses, in a few words (e.g. "any person", \
"person under 21").
- `activity`: the regulated real-world act, normalized to a short phrase so \
it can be matched against the same activity described in other excerpts \
(e.g. "possession of cannabis", "indoor smoking of cannabis"). Use the same \
wording for the same activity across different excerpts you might see.
- `condition`: the single most important logical predicate gating the rule. \
Use {"variable": "age", "operator": ">=", "value": 21} style for numeric \
gates. If the rule is unconditional (applies to everyone, always), return \
{"variable": null, "operator": null, "value": null}.
- `action`: exactly one of "allowed", "prohibited", "required" -- the \
excerpt's bottom-line legal consequence for the activity.
- `scope`: the jurisdiction, copied from the excerpt's given jurisdiction.

Do not add commentary, caveats, or fields beyond the schema. If the excerpt \
describes an exception, encode the EXCEPTION's own condition/action if that \
is the excerpt's main point, otherwise encode the general rule and ignore \
minor carve-outs.
"""


def build_user_message(statute: Statute) -> str:
    return (
        f"Jurisdiction: {statute.jurisdiction}\n"
        f"Citation: {statute.citation}\n"
        f"Excerpt:\n{statute.raw_text}"
    )


def extract_rule(client: anthropic.Anthropic, statute: Statute, model: str = DEFAULT_MODEL) -> Rule:
    """Call Claude once to extract a Rule from one statute excerpt."""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": build_user_message(statute)}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": RULE_JSON_SCHEMA},
            },
        )
    except anthropic.NotFoundError:
        raise RuntimeError(f"Model '{model}' not found -- check LEGALEAN_MODEL / your API access.")
    except anthropic.AuthenticationError:
        raise RuntimeError(
            "Anthropic authentication failed. Set ANTHROPIC_API_KEY to an API key from "
            "console.anthropic.com (a Claude.ai chat subscription does not grant API access)."
        )
    except anthropic.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "unknown")
        raise RuntimeError(f"Rate limited by the Anthropic API; retry after {retry_after}s.")
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Anthropic API error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise RuntimeError("Could not reach the Anthropic API -- check your network connection.")

    text = next(b.text for b in response.content if b.type == "text")
    data = json.loads(text)
    return Rule.from_dict(statute.id, data)


def extract_all(statutes: list[Statute], model: str = DEFAULT_MODEL) -> list[Rule]:
    client = anthropic.Anthropic()
    return [extract_rule(client, statute, model=model) for statute in statutes]
