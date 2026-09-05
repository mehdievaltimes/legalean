"""Plain-Python conflict detection over extracted Rule objects.

No LLM calls happen here -- this module is pure logic over the structured
Rule/Condition objects produced by extract.py (or loaded from a cached
rules.json), so it can be exercised and verified without hitting the API.

Design notes / simplifications (documented, not hidden):
  * Two rules are only compared if their `activity` strings are judged
    "the same real-world act" (see _same_activity) and their `scope`s
    overlap (see scopes.scopes_overlap). We deliberately do NOT require the
    prose `subject` field to match textually -- who a rule applies to is
    already captured structurally in its `condition`, and LLM phrasing of
    `subject` varies too much to string-match reliably.
  * Conditions are treated as ranges over a single variable ("age >= 21" ->
    [21, inf)) for numeric values, or as categorical equality/inequality for
    string values. An unconditional rule ("always applies") is treated as
    overlapping with any condition on the other side, because it covers
    every sub-case the other rule describes.
  * Actions are contradictory when one is "allowed" and the other
    "prohibited", or one is "prohibited" and the other "required". "allowed"
    and "required" are not treated as contradictory (a mandatory act is
    trivially also a permitted one).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import combinations
from typing import Optional

from .models import Condition, Rule
from .scopes import scopes_overlap

_STOPWORDS = {"of", "the", "a", "an", "in", "to", "by", "for", "and", "or"}

_CONTRADICTORY_ACTION_PAIRS = {
    frozenset({"allowed", "prohibited"}),
    frozenset({"prohibited", "required"}),
}


def _normalize_tokens(text: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {tok for tok in cleaned.split() if tok not in _STOPWORDS}


def _same_activity(activity_a: str, activity_b: str, threshold: float = 0.5) -> bool:
    """Heuristic match: normalized token Jaccard similarity above threshold,
    or one phrase contains the other. Good enough for a small sample set;
    would need real NLP (embeddings, canonical activity taxonomy) at scale.
    """
    a, b = _normalize_tokens(activity_a), _normalize_tokens(activity_b)
    if not a or not b:
        return False
    if a <= b or b <= a:  # one is a subset of the other's tokens
        return True
    jaccard = len(a & b) / len(a | b)
    return jaccard >= threshold


def _contradictory_actions(action_a: str, action_b: str) -> bool:
    return frozenset({action_a, action_b}) in _CONTRADICTORY_ACTION_PAIRS


def _numeric_interval(operator: str, value: float) -> tuple[float, bool, float, bool]:
    """Return (low, low_inclusive, high, high_inclusive) for a numeric condition."""
    if operator == ">=":
        return (value, True, math.inf, True)
    if operator == ">":
        return (value, False, math.inf, True)
    if operator == "<=":
        return (-math.inf, True, value, True)
    if operator == "<":
        return (-math.inf, True, value, False)
    if operator == "==":
        return (value, True, value, True)
    raise ValueError(f"unsupported numeric operator for interval conversion: {operator}")


def _intervals_overlap(iv_a: tuple[float, bool, float, bool], iv_b: tuple[float, bool, float, bool]) -> bool:
    lo_a, lo_a_inc, hi_a, hi_a_inc = iv_a
    lo_b, lo_b_inc, hi_b, hi_b_inc = iv_b
    lo = max(lo_a, lo_b)
    hi = min(hi_a, hi_b)
    if lo < hi:
        return True
    if lo == hi:
        lo_inc = lo_a_inc if lo == lo_a else lo_b_inc
        hi_inc = hi_a_inc if hi == hi_a else hi_b_inc
        return lo_inc and hi_inc
    return False


def _condition_overlap(cond_a: Condition, cond_b: Condition) -> bool:
    if cond_a.is_unconditional or cond_b.is_unconditional:
        return True

    if cond_a.variable != cond_b.variable:
        # Different variables (e.g. "age" vs "location"): we can't prove the
        # two conditions are mutually exclusive, so conservatively flag as a
        # possible overlap for a human to review rather than silently drop it.
        return True

    numeric = isinstance(cond_a.value, (int, float)) and isinstance(cond_b.value, (int, float))
    if numeric and cond_a.operator != "!=" and cond_b.operator != "!=":
        return _intervals_overlap(
            _numeric_interval(cond_a.operator, cond_a.value),
            _numeric_interval(cond_b.operator, cond_b.value),
        )

    # Categorical (string) equality/inequality, or a "!=" numeric edge case.
    if cond_a.operator == "==" and cond_b.operator == "==":
        return cond_a.value == cond_b.value
    if cond_a.operator == "==" and cond_b.operator == "!=":
        return cond_a.value != cond_b.value
    if cond_a.operator == "!=" and cond_b.operator == "==":
        return cond_a.value != cond_b.value
    # two "!=" (or anything else unhandled): assume overlap possible.
    return True


@dataclass
class Conflict:
    rule_a: Rule
    rule_b: Rule

    def explain(self) -> str:
        a, b = self.rule_a, self.rule_b
        return (
            f"{a.scope} says the activity is {a.action} "
            f"({a.condition.as_text()}), but {b.scope} says it is {b.action} "
            f"({b.condition.as_text()}) for an overlapping case -- "
            f"the two sources give incompatible answers for the same act."
        )


def find_conflicts(rules: list[Rule]) -> list[Conflict]:
    """Return all pairs of rules that structurally contradict each other.

    A conflict requires ALL of:
      1. scopes overlap (e.g. US Federal law reaches into NY State)
      2. same real-world regulated activity
      3. condition ranges overlap (there exists a case both rules speak to)
      4. actions are logically contradictory (allowed vs prohibited, etc.)
    """
    conflicts: list[Conflict] = []
    for rule_a, rule_b in combinations(rules, 2):
        if rule_a.source_id == rule_b.source_id:
            continue
        if not scopes_overlap(rule_a.scope, rule_b.scope):
            continue
        if not _same_activity(rule_a.activity, rule_b.activity):
            continue
        if not _contradictory_actions(rule_a.action, rule_b.action):
            continue
        if not _condition_overlap(rule_a.condition, rule_b.condition):
            continue
        conflicts.append(Conflict(rule_a=rule_a, rule_b=rule_b))
    return conflicts
