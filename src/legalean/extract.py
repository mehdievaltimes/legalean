"""OPTIONAL: LLM-assisted drafting of a statute file's formalization.

Nothing in the verification pipeline imports this module. The committed
corpus in `statutes/` was formalized by hand and `check_conflicts.py` runs
fully offline; this is a drafting aid for *adding* a new excerpt, and its
output is meant to be reviewed and edited by a human before being trusted.

Usage (requires `pip install anthropic` and an API key -- a Claude.ai chat
subscription does not grant API access):

    export ANTHROPIC_API_KEY=sk-ant-...
    python3 -m legalean.extract path/to/excerpt.txt "US Federal" "8 U.S.C. § 1324a"

It prints proposed frontmatter to stdout. Paste it into a new
`statutes/<id>.md`, add the `## Excerpt` section, and check every field
against the actual citation before committing -- the model's reading of a
statute is a starting point, not an authority.
"""

from __future__ import annotations

import json
import os
import sys

from .models import RULE_JSON_SCHEMA, Condition

DEFAULT_MODEL = os.environ.get("LEGALEAN_MODEL", "claude-opus-5")

SYSTEM_PROMPT = """You are a precise legal-text formalizer. Given one excerpt \
from a statute, extract a single structured rule that captures its core \
logical claim, and return ONLY that rule as JSON matching the provided schema.

Guidance:
- `subject`: who the rule addresses, in a few words (e.g. "any person", \
"state or local peace officer").
- `activity`: the regulated real-world act, normalized to a short phrase so \
it can be matched against the same activity described in other excerpts \
(e.g. "seeking or engaging in unauthorized employment"). Use the same \
wording for the same activity across different excerpts.
- `condition`: the single most important logical predicate gating the rule. \
Use {"variable": "age", "operator": ">=", "value": 18} style for numeric \
gates. If the rule is unconditional (applies to everyone, always), return \
{"variable": null, "operator": null, "value": null}.
- `action`: exactly one of "allowed", "prohibited", "required" -- the \
excerpt's bottom-line legal consequence for the activity. Use "allowed" for \
conduct a scheme deliberately leaves unpunished, and "required" only for an \
affirmative mandate.
- `scope`: the jurisdiction, copied from the excerpt's given jurisdiction.

Do not add commentary, caveats, or fields beyond the schema.
"""


def draft_frontmatter(raw_text: str, jurisdiction: str, citation: str, model: str = DEFAULT_MODEL) -> str:
    """Ask Claude for a proposed formalization, rendered as markdown frontmatter."""
    import anthropic  # imported here so the module is importable without the dependency

    client = anthropic.Anthropic()
    user_message = f"Jurisdiction: {jurisdiction}\nCitation: {citation}\nExcerpt:\n{raw_text}"

    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
            output_config={
                "effort": "low",
                "format": {"type": "json_schema", "schema": RULE_JSON_SCHEMA},
            },
        )
    except anthropic.AuthenticationError:
        raise RuntimeError(
            "Anthropic authentication failed. Set ANTHROPIC_API_KEY to an API key from "
            "console.anthropic.com (a Claude.ai chat subscription does not grant API access)."
        )
    except anthropic.APIStatusError as e:
        raise RuntimeError(f"Anthropic API error ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise RuntimeError("Could not reach the Anthropic API -- check your network connection.")

    data = json.loads(next(b.text for b in response.content if b.type == "text"))
    condition = Condition.from_dict(data["condition"])

    return "\n".join(
        [
            "---",
            "id: TODO-set-an-id-matching-the-filename",
            f"jurisdiction: {jurisdiction}",
            f"citation: {citation}",
            f"subject: {data['subject']}",
            f"activity: {data['activity']}",
            f"condition: {condition.as_text()}",
            f"action: {data['action']}",
            f"scope: {data['scope']}",
            "---",
        ]
    )


def main() -> None:
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    excerpt_path, jurisdiction, citation = sys.argv[1:4]
    raw_text = open(excerpt_path, encoding="utf-8").read().strip()
    try:
        print(draft_frontmatter(raw_text, jurisdiction, citation))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    print("\n# Review every field above against the actual citation before committing.", file=sys.stderr)


if __name__ == "__main__":
    main()
