#!/usr/bin/env python3
"""Manual, dependency-free sanity checks for the pure-Python candidate filter.

Not a pytest suite -- just asserts, runnable with plain `python3`. Verifies
candidates.py (structural pre-filtering) against the shipped sample data and
a few hand-built edge cases. No LLM/API calls and no Lean/subprocess calls --
see test_lean_verification.py for the end-to-end formal-verification check.

    python3 tests/test_candidates_manual.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legalean.candidates import find_candidates  # noqa: E402
from legalean.corpus import load_corpus  # noqa: E402
from legalean.models import Condition, Rule  # noqa: E402

STATUTES_DIR = Path(__file__).parent.parent / "statutes"


def rule(source_id, subject, activity, condition, action, scope) -> Rule:
    var, op, val = condition
    return Rule(
        source_id=source_id,
        subject=subject,
        activity=activity,
        condition=Condition(variable=var, operator=op, value=val),
        action=action,
        scope=scope,
    )


def test_corpus_loads_and_has_expected_candidates():
    statutes, rules = load_corpus(STATUTES_DIR)
    assert len(rules) == len(statutes) == 14, f"expected 14 excerpts, got {len(statutes)}"

    candidates = find_candidates(rules)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in candidates}
    assert frozenset({"us-ina-employment-noncriminalization", "az-sb1070-5c"}) in pairs
    assert frozenset({"us-ina-warrantless-arrest-federal-only", "az-sb1070-6"}) in pairs
    assert frozenset({"us-const-equal-protection-education", "tx-educ-code-21-031"}) in pairs
    assert len(candidates) == 3, f"expected exactly 3 candidates in the corpus, got {len(candidates)}"


def test_corpus_numeric_condition_pair_gets_a_witness():
    """The Plyler pair is the only real conflict with a numeric condition
    (Tex. Educ. Code § 21.031's `age > 5`), so its proof needs an omega witness."""
    _, rules = load_corpus(STATUTES_DIR)
    plyler = next(
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id}
        == {"us-const-equal-protection-education", "tx-educ-code-21-031"}
    )
    assert plyler.witness == 6, f"expected witness 6 for `age > 5`, got {plyler.witness}"


def test_corpus_spans_three_jurisdictions():
    _, rules = load_corpus(STATUTES_DIR)
    assert {r.scope for r in rules} == {"US Federal", "Arizona State", "Texas State"}


def test_corpus_compatible_pairs_are_not_candidates():
    """The two real allowed/required pairs (upheld state laws) must stay silent."""
    _, rules = load_corpus(STATUTES_DIR)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in find_candidates(rules)}
    assert frozenset({"us-irca-everify-voluntary", "az-legal-workers-act-everify"}) not in pairs
    assert frozenset({"us-ina-state-cooperation-permitted", "az-sb1070-2b"}) not in pairs


def test_corpus_documented_false_negatives_stay_silent():
    """Both sides are `prohibited` in each pair, so this tool finds nothing.
    One is field preemption (registration), one is a dropped federal exemption
    (harboring) -- see README limitations."""
    _, rules = load_corpus(STATUTES_DIR)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in find_candidates(rules)}
    assert frozenset({"us-ina-alien-registration", "az-sb1070-3"}) not in pairs
    assert frozenset({"us-ina-harboring", "az-sb1070-13-2929"}) not in pairs


def test_corpus_round_trips_conditions():
    """Compact frontmatter condition syntax survives parse -> render."""
    _, rules = load_corpus(STATUTES_DIR)
    by_id = {r.source_id: r for r in rules}
    assert by_id["us-ina-alien-registration"].condition.as_text() == "age >= 18"
    assert by_id["az-sb1070-3"].condition.as_text() == "always"


def test_classic_overlapping_age_gate_is_a_candidate_with_a_witness():
    # "allowed if age >= 18" vs "prohibited if age < 21" -- ages 18-20 are contradictory.
    a = rule("a", "adult", "drinking alcohol", ("age", ">=", 18), "allowed", "US Federal")
    b = rule("b", "minor", "drinking alcohol", ("age", "<", 21), "prohibited", "US Federal")
    candidates = find_candidates([a, b])
    assert len(candidates) == 1
    assert candidates[0].witness == 18


def test_non_overlapping_age_ranges_are_not_a_candidate():
    # "allowed if age >= 21" vs "prohibited if age < 21" partition perfectly -- no witness exists.
    a = rule("a", "adult", "possession of X", ("age", ">=", 21), "allowed", "Arizona State")
    b = rule("b", "minor", "possession of X", ("age", "<", 21), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_same_action_is_not_a_candidate():
    a = rule("a", "any person", "some activity", (None, None, None), "prohibited", "US Federal")
    b = rule("b", "some subset", "some activity", ("age", "<", 21), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_unrelated_activities_are_not_a_candidate():
    a = rule("a", "any person", "seeking unauthorized employment", (None, None, None), "allowed", "US Federal")
    b = rule("b", "any person", "filing a tax return", ("day", ">=", 1), "required", "Arizona State")
    assert find_candidates([a, b]) == []


def test_non_overlapping_scopes_are_not_a_candidate():
    a = rule("a", "any person", "jaywalking", (None, None, None), "prohibited", "California")
    b = rule("b", "any person", "jaywalking", (None, None, None), "allowed", "Arizona State")
    assert find_candidates([a, b]) == []


def test_different_condition_variables_are_not_a_candidate():
    # Same activity/scope/contradictory actions, but conditions on unrelated variables --
    # out of scope for this tool's condition model (see candidates.py docstring / README).
    a = rule("a", "any person", "some activity", ("age", ">=", 18), "allowed", "US Federal")
    b = rule("b", "any person", "some activity", ("income", "<", 50000), "prohibited", "US Federal")
    assert find_candidates([a, b]) == []


def run_all():
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL: {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
