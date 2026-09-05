"""Data model for statute excerpts and extracted rules.

The extracted-rule schema is intentionally small and flat so it can be
validated and compared without any NLP/LLM involvement once extraction
is done. See RULE_JSON_SCHEMA below for the exact shape the extraction
prompt asks the model to return.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

Action = Literal["allowed", "prohibited", "required"]
Operator = Literal[">=", ">", "<=", "<", "==", "!="]

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
            "description": "Jurisdiction/context the rule is in force in, e.g. 'US Federal', 'NY State'.",
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
        if self.is_unconditional:
            return "always"
        val = f"'{self.value}'" if isinstance(self.value, str) else self.value
        return f"{self.variable} {self.operator} {val}"

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Condition":
        return Condition(
            variable=d.get("variable"),
            operator=d.get("operator"),
            value=d.get("value"),
        )

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

    @staticmethod
    def from_dict(source_id: str, d: dict[str, Any]) -> "Rule":
        return Rule(
            source_id=source_id,
            subject=d["subject"],
            activity=d["activity"],
            condition=Condition.from_dict(d["condition"]),
            action=d["action"],
            scope=d["scope"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "subject": self.subject,
            "activity": self.activity,
            "condition": self.condition.to_dict(),
            "action": self.action,
            "scope": self.scope,
        }

    def as_text(self) -> str:
        return f"[{self.scope}] {self.subject}: {self.action} to {self.activity} if {self.condition.as_text()}"
