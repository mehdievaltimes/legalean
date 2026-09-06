"""Data model for statute excerpts and extracted rules.

The extracted-rule schema is intentionally small and flat so it can be
validated and compared without any NLP/LLM involvement once extraction
is done. See RULE_JSON_SCHEMA below for the exact shape the extraction
prompt asks the model to return.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal, Optional

Action = Literal["allowed", "prohibited", "required"]
Operator = Literal[">=", ">", "<=", "<", "==", "!="]

ACTIONS = ("allowed", "prohibited", "required")

# Matches the compact condition syntax used in statute-markdown frontmatter,
# e.g. `age >= 18`, `religious_volunteer == true`, `basis == "residence"`.
# Order matters: two-character operators must be tried before their
# one-character prefixes.
_CONDITION_RE = re.compile(r'^(\w+)\s*(>=|<=|==|!=|>|<)\s*(-?\d+|"[^"]*"|true|false)$')

# Categorical (non-numeric) values admit only equality and inequality --
# "basis > 'residence'" is meaningless, so it is rejected at parse time
# rather than silently producing an unprovable Lean goal.
_EQUALITY_OPERATORS = ("==", "!=")

# Documented JSON schema the extraction LLM call must satisfy (informal --
# expressed as a plain dict since we keep dependencies minimal and avoid
# a JSON-schema validation library).
RULE_JSON_SCHEMA = {
    "type": "object",
    "required": ["subject", "activity", "condition", "action", "scope"],
    "properties": {
        "subject": {
            "type": "string",
            "description": "Who the rule applies to, e.g. 'any person', 'person under 21'.",
        },
        "activity": {
            "type": "string",
            "description": (
                "The regulated activity/topic in a few normalized words, e.g. "
                "'possession of cannabis', 'indoor smoking of cannabis'. Used to "
                "match rules that govern the same real-world act across sources."
            ),
        },
        "condition": {
            "type": "object",
            "required": ["variable", "operator", "value"],
            "description": (
                "A single simple logical predicate, or null/null/null for an "
                "unconditional rule that always applies."
            ),
            "properties": {
                "variable": {"type": ["string", "null"], "description": "e.g. 'age'"},
                "operator": {
                    "type": ["string", "null"],
                    "enum": [">=", ">", "<=", "<", "==", "!=", None],
                },
                "value": {"type": ["number", "string", "null"]},
            },
        },
        "action": {
            "type": "string",
            "enum": ["allowed", "prohibited", "required"],
        },
        "scope": {
            "type": "string",
            "description": "Jurisdiction/context the rule is in force in, e.g. 'US Federal', 'Arizona State'.",
        },
        "exclusive": {
            "type": "boolean",
            "description": (
                "Optional, default false. True when this sovereign occupies the whole "
                "field, displacing any rule on the same activity from an enclosed "
                "jurisdiction even one that agrees. This encodes a judicial holding, "
                "not statutory text -- see README."
            ),
        },
    },
}


@dataclass
class Statute:
    id: str
    jurisdiction: str
    citation: str
    raw_text: str

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Statute":
        return Statute(
            id=d["id"],
            jurisdiction=d["jurisdiction"],
            citation=d["citation"],
            raw_text=d["raw_text"],
        )


@dataclass
class Condition:
    variable: Optional[str]
    operator: Optional[Operator]
    value: Optional[Any]

    @property
    def is_unconditional(self) -> bool:
        return self.variable is None or self.operator is None

    def as_text(self) -> str:
        """Render back to the compact frontmatter syntax; inverse of from_text."""
        if self.is_unconditional:
            return "always"
        if isinstance(self.value, bool):  # check before int -- bool is an int subclass
            val = "true" if self.value else "false"
        elif isinstance(self.value, str):
            val = f'"{self.value}"'
        else:
            val = str(self.value)
        return f"{self.variable} {self.operator} {val}"

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Condition":
        return Condition(
            variable=d.get("variable"),
            operator=d.get("operator"),
            value=d.get("value"),
        )

    @staticmethod
    def from_text(text: str) -> "Condition":
        """Parse the compact form used in statute-markdown frontmatter.

        `always`                        -> unconditional
        `age >= 18`                     -> numeric predicate
        `religious_volunteer == true`   -> boolean predicate
        `basis == "residence"`          -> string predicate

        The inverse of `as_text()`, so a corpus round-trips.
        """
        text = text.strip()
        if text in ("always", ""):
            return Condition(variable=None, operator=None, value=None)

        match = _CONDITION_RE.match(text)
        if not match:
            raise ValueError(
                f"cannot parse condition {text!r}; expected 'always' or "
                f"'<variable> <op> <number|true|false|\"string\">' with op in "
                f">=, >, <=, <, ==, !="
            )
        variable, operator, raw_value = match.groups()
        value: Any
        if raw_value.startswith('"'):
            value = raw_value[1:-1]
        elif raw_value in ("true", "false"):
            value = raw_value == "true"
        else:
            value = int(raw_value)

        if not isinstance(value, int) or isinstance(value, bool):
            if operator not in _EQUALITY_OPERATORS:
                raise ValueError(
                    f"condition {text!r}: operator {operator!r} needs a numeric value; "
                    f"categorical values support only {' and '.join(_EQUALITY_OPERATORS)}"
                )
        return Condition(variable=variable, operator=operator, value=value)

    def to_dict(self) -> dict[str, Any]:
        return {"variable": self.variable, "operator": self.operator, "value": self.value}


@dataclass
class Rule:
    source_id: str  # links back to Statute.id
    subject: str
    activity: str
    condition: Condition
    action: Action
    scope: str
    # True when this rule's sovereign claims the whole regulatory field, so
    # that ANY rule from an enclosed jurisdiction on the same activity is
    # displaced regardless of what it says. See README -- unlike every other
    # field, this one encodes a judicial holding rather than statutory text.
    exclusive: bool = False

    @staticmethod
    def from_dict(source_id: str, d: dict[str, Any]) -> "Rule":
        return Rule(
            source_id=source_id,
            subject=d["subject"],
            activity=d["activity"],
            condition=Condition.from_dict(d["condition"]),
            action=d["action"],
            scope=d["scope"],
            exclusive=bool(d.get("exclusive", False)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "subject": self.subject,
            "activity": self.activity,
            "condition": self.condition.to_dict(),
            "action": self.action,
            "scope": self.scope,
            "exclusive": self.exclusive,
        }

    def as_text(self) -> str:
        exclusive = " [exclusive field]" if self.exclusive else ""
        return (
            f"[{self.scope}] {self.subject}: {self.action} to {self.activity} "
            f"if {self.condition.as_text()}{exclusive}"
        )
