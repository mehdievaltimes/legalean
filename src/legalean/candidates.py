"""Plain-Python candidate filtering over extracted Rule objects.

No LLM calls happen here. This module does NOT decide whether two rules
actually conflict -- that verdict is left to Lean (see leangen.py /
leanverify.py), which formally proves or fails to prove the contradiction.
This module's only job is cheap, syntactic pre-filtering: which pairs are
even worth generating a Lean theorem for, plus (when possible) a concrete
witness for Lean to check with `omega` (numeric) or `decide` (categorical).

Design notes / simplifications (documented, not hidden):
  * Two rules are only compared if their `activity` strings are judged
    "the same real-world act" (see _same_activity) and their `scope`s
    overlap (see scopes.scopes_overlap). We deliberately do NOT require the
    prose `subject` field to match textually -- who a rule applies to is
    already captured structurally in its `condition`, and LLM phrasing of
    `subject` varies too much to string-match reliably.
  * A candidate is only emitted when we can construct a concrete witness --
    i.e. when we can hand Lean something it can actually check. Conditions
    may be numeric (Int, compared as intervals), boolean, or string; the
    latter two are compared by equality/inequality. Conditions on different
    variables, or on the same variable formalized at two different types,
    are NOT modeled and are silently excluded rather than guessed at (see
    README limitations).
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
from typing import Any, Optional

from .models import Condition, Rule
from .scopes import enclosing_first, scopes_overlap

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


@dataclass
class Witness:
    """A concrete value satisfying both rules' conditions, plus the Lean type
    it inhabits. Lean re-checks that it really does satisfy them -- see
    leangen.py / leanverify.py -- so this is a proof hint, not a proof."""

    value: Any
    lean_type: str  # "Int" | "Bool" | "String"


def _value_kind(value: Any) -> Optional[str]:
    """The Lean type a condition value inhabits, or None if unsupported."""
    if isinstance(value, bool):  # must precede int -- bool is an int subclass
        return "Bool"
    if isinstance(value, (int, float)):
        return "Int"
    if isinstance(value, str):
        return "String"
    return None


def _categorical_witness_for_single(operator: str, value: Any, kind: str) -> Optional[Any]:
    """A concrete value satisfying one categorical condition on its own."""
    if operator == "==":
        return value
    if operator == "!=":
        if kind == "Bool":
            return not value
        return value + "_"  # any strictly longer string necessarily differs
    return None


def _categorical_witness(cond_a: Condition, cond_b: Condition, kind: str) -> Optional[Any]:
    """A concrete value satisfying two categorical conditions on the same variable."""
    if cond_a.operator not in ("==", "!=") or cond_b.operator not in ("==", "!="):
        return None
    a_val, b_val = cond_a.value, cond_b.value

    if cond_a.operator == "==" and cond_b.operator == "==":
        return a_val if a_val == b_val else None
    if cond_a.operator == "==":  # b is !=
        return a_val if a_val != b_val else None
    if cond_b.operator == "==":  # a is !=
        return b_val if a_val != b_val else None

    # both "!=": need a value distinct from each excluded one.
    if kind == "Bool":
        # Only two inhabitants, so this is satisfiable only when both exclude
        # the same value.
        return (not a_val) if a_val == b_val else None
    longest = max(a_val, b_val, key=len)
    return longest + "_"


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


def _witness_for_single(cond: Condition) -> Optional[Witness]:
    """A witness satisfying one condition on its own (the other side being unconditional)."""
    kind = _value_kind(cond.value)
    if kind is None:
        return None
    if kind == "Int":
        if cond.operator == "!=":
            return None  # not modeled as an interval
        return Witness(_numeric_witness_for_single(cond.operator, cond.value), "Int")
    value = _categorical_witness_for_single(cond.operator, cond.value, kind)
    return None if value is None else Witness(value, kind)


def _find_witness(cond_a: Condition, cond_b: Condition) -> Optional[Witness]:
    """A concrete value satisfying both conditions, or None if we can't construct
    one (different variables, mismatched value types, or genuinely no overlap).

    An unconditional rule constrains nothing, so it defers entirely to the
    other side; two unconditional rules are satisfied by anything.
    """
    if cond_a.is_unconditional and cond_b.is_unconditional:
        return Witness(0, "Int")
    if cond_a.is_unconditional:
        return _witness_for_single(cond_b)
    if cond_b.is_unconditional:
        return _witness_for_single(cond_a)

    if cond_a.variable != cond_b.variable:
        return None  # different variables -- out of scope, see module docstring
    kind_a, kind_b = _value_kind(cond_a.value), _value_kind(cond_b.value)
    if kind_a is None or kind_a != kind_b:
        return None  # unsupported, or the same variable formalized at two types

    if kind_a != "Int":
        value = _categorical_witness(cond_a, cond_b, kind_a)
        return None if value is None else Witness(value, kind_a)

    if cond_a.operator == "!=" or cond_b.operator == "!=":
        return None  # not modeled as an interval

    lo_a, lo_a_inc, hi_a, hi_a_inc = _numeric_interval(cond_a.operator, cond_a.value)
    lo_b, lo_b_inc, hi_b, hi_b_inc = _numeric_interval(cond_b.operator, cond_b.value)
    lo = max(lo_a, lo_b)
    hi = min(hi_a, hi_b)
    lo_inc = lo_a_inc if lo == lo_a else lo_b_inc
    hi_inc = hi_a_inc if hi == hi_a else hi_b_inc
    value = _witness_in_interval(lo, lo_inc, hi, hi_inc)
    return None if value is None else Witness(value, "Int")


@dataclass
class Candidate:
    """A structurally plausible conflict, pending Lean's formal verdict."""

    rule_a: Rule
    rule_b: Rule
    witness: Witness  # concrete value satisfying both conditions, plus its Lean type


def find_candidates(rules: list[Rule]) -> list[Candidate]:
    """Return rule pairs worth generating a Lean conflict theorem for.

    A candidate requires ALL of:
      1. scopes overlap (e.g. US Federal law reaches into Arizona State)
      2. same real-world regulated activity
      3. actions are logically contradictory (allowed vs prohibited, etc.)
      4. a concrete witness can be constructed for both conditions -- they
         are unconditional, or on the same variable at the same type, and
         provably overlap

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
        # Present the enclosing jurisdiction first -- readability only, not a
        # statement about which rule prevails (see scopes.enclosing_first).
        first, second = (
            (rule_a, rule_b) if enclosing_first(rule_a.scope, rule_b.scope) else (rule_b, rule_a)
        )
        candidates.append(Candidate(rule_a=first, rule_b=second, witness=witness))
    return candidates
