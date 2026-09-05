"""Plain-Python candidate filtering over extracted Rule objects.

No LLM calls happen here. This module does NOT decide whether two rules
actually conflict -- that verdict is left to Lean (see leangen.py /
leanverify.py), which formally proves or fails to prove the contradiction.
This module's only job is cheap, syntactic pre-filtering: which pairs are
even worth generating a Lean theorem for, plus (when possible) a concrete
integer witness for Lean's `omega` tactic to check.

Design notes / simplifications (documented, not hidden):
  * Two rules are only compared if their `activity` strings are judged
    "the same real-world act" (see _same_activity) and their `scope`s
    overlap (see scopes.scopes_overlap). We deliberately do NOT require the
    prose `subject` field to match textually -- who a rule applies to is
    already captured structurally in its `condition`, and LLM phrasing of
    `subject` varies too much to string-match reliably.
  * A candidate is only emitted when we can construct a concrete integer
    witness (or determine both sides are unconditional) -- i.e. when we can
    hand Lean something it can actually check. Conditions on different
    variables, or non-numeric (categorical) conditions, are NOT modeled and
    are silently excluded rather than guessed at (see README limitations).
  * Actions are contradictory when one is "allowed" and the other
    "prohibited", or one is "prohibited" and the other "required". "allowed"
    and "required" are not treated as contradictory (a mandatory act is
    trivially also a permitted one) -- this matches the exclusion axioms in
    lean/Legalean/Deontic.lean.
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


def _numeric_witness_for_single(operator: str, value: float) -> int:
    """A concrete integer satisfying a single numeric condition on its own."""
    if operator == ">=":
        return int(value)
    if operator == ">":
        return int(value) + 1
    if operator == "<=":
        return int(value)
    if operator == "<":
        return int(value) - 1
    if operator == "==":
        return int(value)
    if operator == "!=":
        return int(value) + 1
    raise ValueError(f"unsupported operator: {operator}")


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


def _witness_in_interval(lo: float, lo_inc: bool, hi: float, hi_inc: bool) -> Optional[int]:
    """A concrete integer inside [lo, hi] (respecting inclusivity), or None if empty/unbounded-empty."""
    if lo > hi or (lo == hi and not (lo_inc and hi_inc)):
        return None
    if lo == -math.inf and hi == math.inf:
        return 0
    if lo == -math.inf:
        return int(hi) if hi_inc else int(hi) - 1
    if hi == math.inf:
        return int(lo) if lo_inc else int(lo) + 1
    candidate = int(lo) if lo_inc else int(lo) + 1
    if candidate > hi or (candidate == hi and not hi_inc):
        return None
    return candidate


def _find_witness(cond_a: Condition, cond_b: Condition) -> Optional[int]:
    """A concrete integer satisfying both conditions, or None if we can't construct one
    (different variables, non-numeric values, or genuinely no overlap)."""
    if cond_a.is_unconditional and cond_b.is_unconditional:
        return 0
    if cond_a.is_unconditional:
        cond_b_value = cond_b.value
        if not isinstance(cond_b_value, (int, float)) or cond_b.operator == "!=":
            return None
        return _numeric_witness_for_single(cond_b.operator, cond_b_value)
    if cond_b.is_unconditional:
        return _find_witness(cond_b, cond_a)

    if cond_a.variable != cond_b.variable:
        return None  # different variables -- out of scope, see module docstring
    a_val, b_val = cond_a.value, cond_b.value
    if not (isinstance(a_val, (int, float)) and isinstance(b_val, (int, float))):
        return None  # categorical conditions -- out of scope, see module docstring
    if cond_a.operator == "!=" or cond_b.operator == "!=":
        return None  # not modeled as an interval

    lo_a, lo_a_inc, hi_a, hi_a_inc = _numeric_interval(cond_a.operator, a_val)
    lo_b, lo_b_inc, hi_b, hi_b_inc = _numeric_interval(cond_b.operator, b_val)
    lo = max(lo_a, lo_b)
    hi = min(hi_a, hi_b)
    lo_inc = lo_a_inc if lo == lo_a else lo_b_inc
    hi_inc = hi_a_inc if hi == hi_a else hi_b_inc
    return _witness_in_interval(lo, lo_inc, hi, hi_inc)


@dataclass
class Candidate:
    """A structurally plausible conflict, pending Lean's formal verdict."""

    rule_a: Rule
    rule_b: Rule
    witness: int  # concrete Int satisfying both conditions (arbitrary, e.g. 0, if both are unconditional)


def find_candidates(rules: list[Rule]) -> list[Candidate]:
    """Return rule pairs worth generating a Lean conflict theorem for.

    A candidate requires ALL of:
      1. scopes overlap (e.g. US Federal law reaches into Arizona State)
      2. same real-world regulated activity
      3. actions are logically contradictory (allowed vs prohibited, etc.)
      4. a concrete integer witness can be constructed for both conditions
         (i.e. the conditions are unconditional, or numeric on the same
         variable, and provably overlap)

    This is NOT the final verdict -- it's the set of pairs handed to
    leangen.py / leanverify.py for actual formal verification.
    """
    candidates: list[Candidate] = []
    for rule_a, rule_b in combinations(rules, 2):
        if rule_a.source_id == rule_b.source_id:
            continue
        if not scopes_overlap(rule_a.scope, rule_b.scope):
            continue
        if not _same_activity(rule_a.activity, rule_b.activity):
            continue
        if not _contradictory_actions(rule_a.action, rule_b.action):
            continue
        witness = _find_witness(rule_a.condition, rule_b.condition)
        if witness is None:
            continue  # no constructible overlap witness (see _find_witness docstring for why)
        candidates.append(Candidate(rule_a=rule_a, rule_b=rule_b, witness=witness))
    return candidates
