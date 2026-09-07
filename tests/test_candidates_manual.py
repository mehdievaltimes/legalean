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

from legalean.candidates import (  # noqa: E402
    CONTRADICTION,
    PREEMPTION,
    _find_witness,
    _same_activity,
    _within_field,
    find_candidates,
    find_near_miss_activities,
)
from legalean.corpus import load_corpus  # noqa: E402
from legalean.models import Condition, Rule  # noqa: E402
from legalean.scopes import scopes_overlap, strictly_encloses  # noqa: E402

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
    assert len(rules) == len(statutes) == 24, f"expected 24 excerpts, got {len(statutes)}"

    candidates = find_candidates(rules)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in candidates}
    assert frozenset({"us-ina-employment-noncriminalization", "az-sb1070-5c"}) in pairs
    assert frozenset({"us-ina-employment-noncriminalization", "al-hb56-11a"}) in pairs
    assert frozenset({"us-ina-warrantless-arrest-federal-only", "az-sb1070-6"}) in pairs
    assert frozenset({"us-const-equal-protection-education", "tx-educ-code-21-031"}) in pairs
    assert frozenset({"us-const-equal-protection-school-status-check", "al-hb56-28"}) in pairs
    assert frozenset({"us-ina-harboring-religious-exemption", "az-sb1070-13-2929"}) in pairs
    assert frozenset({"us-ina-alien-registration", "az-sb1070-3"}) in pairs
    assert frozenset({"us-ina-alien-registration", "al-hb56-10"}) in pairs
    assert frozenset({"us-ina-harboring", "az-sb1070-13-2929"}) in pairs
    assert frozenset({"us-ina-harboring", "sc-act69-4bd"}) in pairs
    assert frozenset({"us-ina-harboring", "ga-hb87-7"}) in pairs
    assert frozenset({"us-fraudulent-immigration-documents", "sc-act69-6b2"}) in pairs
    assert frozenset({"us-ina-alien-registration", "sc-act69-5"}) in pairs
    assert len(candidates) == 13, f"expected exactly 13 candidates in the corpus, got {len(candidates)}"


def test_one_federal_rule_fans_out_to_multiple_states():
    """The federal employment rule conflicts with both Arizona's and Alabama's
    parallel offenses -- one formalized rule checked against every state."""
    _, rules = load_corpus(STATUTES_DIR)
    states = {
        (c.rule_a if c.rule_b.source_id == "us-ina-employment-noncriminalization" else c.rule_b).scope
        for c in find_candidates(rules)
        if "us-ina-employment-noncriminalization" in {c.rule_a.source_id, c.rule_b.source_id}
    }
    assert states == {"Arizona State", "Alabama State"}


def test_two_states_are_never_compared_to_each_other():
    """Arizona and Alabama both prohibit unauthorized work, but one state's law
    has no force in another, so scopes must not overlap."""
    _, rules = load_corpus(STATUTES_DIR)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in find_candidates(rules)}
    assert frozenset({"az-sb1070-5c", "al-hb56-11a"}) not in pairs
    assert not scopes_overlap("Arizona State", "Alabama State")


def test_corpus_covers_both_exclusion_axioms():
    """Three conflicts are allowed/prohibited; the Alabama pair is the only
    prohibited/required one, so it is what exercises prohibited_required_excl."""
    _, rules = load_corpus(STATUTES_DIR)
    action_pairs = [frozenset({c.rule_a.action, c.rule_b.action}) for c in find_candidates(rules)]
    assert frozenset({"allowed", "prohibited"}) in action_pairs
    assert frozenset({"prohibited", "required"}) in action_pairs


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
    assert plyler.witness.value == 6, f"expected witness 6 for `age > 5`, got {plyler.witness}"
    assert plyler.witness.lean_type == "Int"


def test_corpus_spans_six_jurisdictions():
    _, rules = load_corpus(STATUTES_DIR)
    assert {r.scope for r in rules} == {
        "US Federal",
        "Arizona State",
        "Texas State",
        "Alabama State",
        "South Carolina State",
        "Georgia State",
    }


def test_narrower_offenses_are_preempted_but_do_not_contradict():
    """South Carolina's and Georgia's harboring offenses each carry an extra
    element, so each is inside the occupied field (preempted) but cannot be
    shown to contradict the religious safe harbor (unverifiable, so silent)."""
    _, rules = load_corpus(STATUTES_DIR)
    for narrower in ("sc-act69-4bd", "ga-hb87-7"):
        against = {
            (c.kind, c.rule_a.source_id)
            for c in find_candidates(rules)
            if narrower in {c.rule_a.source_id, c.rule_b.source_id}
        }
        assert against == {(PREEMPTION, "us-ina-harboring")}, f"{narrower}: {against}"


def test_harboring_field_displaces_three_states():
    """One `exclusive` federal rule reaches Arizona, South Carolina and
    Georgia -- two of them via narrower, specialized activity keys."""
    _, rules = load_corpus(STATUTES_DIR)
    displaced = {
        c.rule_b.scope
        for c in find_candidates(rules)
        if c.kind == PREEMPTION and c.rule_a.source_id == "us-ina-harboring"
    }
    assert displaced == {"Arizona State", "South Carolina State", "Georgia State"}


def test_field_membership_is_directional():
    """A narrower act is inside a broader field; the reverse is not true."""
    field = "harboring or transporting an unlawfully present alien"
    narrower = field + " with intent to further unlawful entry"
    assert _within_field(field, narrower)
    assert not _within_field(narrower, field)
    assert _within_field(field, field), "a field contains itself"
    # ...and the contradiction path still refuses the same pair.
    assert not _same_activity(field, narrower)


def test_intended_specialization_is_not_reported_as_a_near_miss():
    """A narrower activity inside a declared field is by design, not a typo."""
    federal = rule("f", "x", "harboring an alien", (None, None, None), "prohibited", "US Federal")
    federal.exclusive = True
    state = rule(
        "s", "x", "harboring an alien with intent to avoid detection",
        (None, None, None), "prohibited", "Arizona State",
    )
    assert find_near_miss_activities([federal, state]) == []
    # Without the field declaration it *is* a near miss worth flagging.
    federal.exclusive = False
    assert len(find_near_miss_activities([federal, state])) == 1


def test_corpus_compatible_pairs_are_not_candidates():
    """The two real allowed/required pairs (upheld state laws) must stay silent."""
    _, rules = load_corpus(STATUTES_DIR)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in find_candidates(rules)}
    assert frozenset({"us-irca-everify-voluntary", "az-legal-workers-act-everify"}) not in pairs
    assert frozenset({"us-ina-state-cooperation-permitted", "az-sb1070-2b"}) not in pairs


def test_corpus_registration_pair_is_field_preemption_not_contradiction():
    """Both sides say `prohibited`, so there is no deontic contradiction --
    the pair is caught only because the federal scheme occupies the field."""
    _, rules = load_corpus(STATUTES_DIR)
    pair = next(
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id} == {"us-ina-alien-registration", "az-sb1070-3"}
    )
    assert pair.kind == PREEMPTION
    assert pair.rule_a.action == pair.rule_b.action == "prohibited"
    # rule_a is always the exclusive/occupying rule for a preemption candidate.
    assert pair.rule_a.source_id == "us-ina-alien-registration" and pair.rule_a.exclusive
    assert pair.rule_b.source_id == "az-sb1070-3" and not pair.rule_b.exclusive


def test_one_exclusive_rule_preempts_across_states():
    """The preemption analogue of fan-out: a single `exclusive` federal rule
    displaces parallel registration offenses in three states at once."""
    _, rules = load_corpus(STATUTES_DIR)
    displaced = {
        c.rule_b.source_id: c.rule_b.scope
        for c in find_candidates(rules)
        if c.kind == PREEMPTION and c.rule_a.source_id == "us-ina-alien-registration"
    }
    assert displaced == {
        "az-sb1070-3": "Arizona State",
        "al-hb56-10": "Alabama State",
        "sc-act69-5": "South Carolina State",
    }


def test_parallel_state_registration_offenses_are_not_compared():
    """Arizona's and Alabama's registration offenses agree and neither claims
    exclusivity, so they must never be paired with each other."""
    _, rules = load_corpus(STATUTES_DIR)
    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in find_candidates(rules)}
    assert frozenset({"az-sb1070-3", "al-hb56-10"}) not in pairs


def test_exclusive_flags_stay_rare_and_deliberate():
    """`exclusive` encodes a judicial holding, so each one is a deliberate act."""
    _, rules = load_corpus(STATUTES_DIR)
    assert sorted(r.source_id for r in rules if r.exclusive) == [
        "us-fraudulent-immigration-documents",
        "us-ina-alien-registration",
        "us-ina-harboring",
    ]


def test_preemption_covers_three_distinct_fields():
    """The exclusive mechanism is not special-cased to one field: registration,
    harboring and document fraud are each occupied, by different federal rules."""
    _, rules = load_corpus(STATUTES_DIR)
    fields = {
        c.rule_a.activity for c in find_candidates(rules) if c.kind == PREEMPTION
    }
    assert fields == {
        "failing to carry alien registration document",
        "harboring or transporting an unlawfully present alien",
        "possessing or using a fraudulent immigration document",
    }


def test_one_state_act_can_intrude_on_every_field():
    """S.C. Act 69 appears three times, once in each occupied field, each
    declared by a different federal rule."""
    _, rules = load_corpus(STATUTES_DIR)
    by_field = {
        c.rule_b.source_id: c.rule_a.source_id
        for c in find_candidates(rules)
        if c.kind == PREEMPTION and c.rule_b.source_id.startswith("sc-act69")
    }
    assert by_field == {
        "sc-act69-4bd": "us-ina-harboring",
        "sc-act69-6b2": "us-fraudulent-immigration-documents",
        "sc-act69-5": "us-ina-alien-registration",
    }


def test_witness_from_intersecting_two_numeric_conditions():
    """S.C. Act 69 § 5 states its own `age >= 18`, matching the federal rule's,
    so this is the only corpus pair whose witness comes from intersecting two
    intervals rather than satisfying one condition alone."""
    _, rules = load_corpus(STATUTES_DIR)
    by_id = {r.source_id: r for r in rules}
    federal, state = by_id["us-ina-alien-registration"], by_id["sc-act69-5"]
    assert not federal.condition.is_unconditional and not state.condition.is_unconditional
    assert federal.condition.as_text() == state.condition.as_text() == "age >= 18"

    pair = next(
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id} == {"us-ina-alien-registration", "sc-act69-5"}
    )
    assert pair.witness.lean_type == "Int" and pair.witness.value == 18

    # Every other corpus pair has at least one unconditional side.
    both_conditional = [
        c
        for c in find_candidates(rules)
        if not c.rule_a.condition.is_unconditional and not c.rule_b.condition.is_unconditional
    ]
    assert len(both_conditional) == 1


def test_one_provision_can_be_caught_on_two_independent_grounds():
    """A.R.S. § 13-2929 is displaced by the federal field claim AND contradicts
    the religious safe harbor -- which is how the Ninth Circuit decided it."""
    _, rules = load_corpus(STATUTES_DIR)
    against = {
        (c.kind, c.rule_a.source_id)
        for c in find_candidates(rules)
        if "az-sb1070-13-2929" in {c.rule_a.source_id, c.rule_b.source_id}
    }
    assert against == {
        (PREEMPTION, "us-ina-harboring"),
        (CONTRADICTION, "us-ina-harboring-religious-exemption"),
    }


def test_preemption_needs_strict_enclosure():
    """A sovereign never preempts itself, and states never preempt each other."""
    assert strictly_encloses("US Federal", "Arizona State")
    assert not strictly_encloses("US Federal", "US Federal")
    assert not strictly_encloses("Arizona State", "US Federal")
    assert not strictly_encloses("Arizona State", "Alabama State")

    # Two federal rules on the same activity, one exclusive: not a preemption.
    a = rule("a", "x", "act", (None, None, None), "prohibited", "US Federal")
    a.exclusive = True
    b = rule("b", "x", "act", (None, None, None), "prohibited", "US Federal")
    assert find_candidates([a, b]) == []

    # A state cannot preempt the federal government.
    c = rule("c", "x", "act", (None, None, None), "prohibited", "Arizona State")
    c.exclusive = True
    d = rule("d", "x", "act", (None, None, None), "prohibited", "US Federal")
    assert find_candidates([c, d]) == []


def test_preemption_fires_regardless_of_the_displaced_action():
    """The point of field preemption: content of the state rule is irrelevant."""
    federal = rule("f", "x", "act", (None, None, None), "prohibited", "US Federal")
    federal.exclusive = True
    for action in ("allowed", "prohibited", "required"):
        state = rule("s", "x", "act", (None, None, None), action, "Arizona State")
        candidates = find_candidates([federal, state])
        assert len(candidates) == 1, f"expected a candidate for state action {action}"
        assert candidates[0].kind == PREEMPTION


def test_preemption_takes_precedence_over_contradiction():
    """When a pair is both, only the preemption candidate is emitted."""
    federal = rule("f", "x", "act", (None, None, None), "prohibited", "US Federal")
    federal.exclusive = True
    state = rule("s", "x", "act", (None, None, None), "allowed", "Arizona State")
    candidates = find_candidates([federal, state])
    assert len(candidates) == 1
    assert candidates[0].kind == PREEMPTION


def test_non_exclusive_same_action_pair_is_still_silent():
    """Without the exclusive flag, agreeing rules remain a non-conflict."""
    federal = rule("f", "x", "act", (None, None, None), "prohibited", "US Federal")
    state = rule("s", "x", "act", (None, None, None), "prohibited", "Arizona State")
    assert find_candidates([federal, state]) == []


def test_other_corpus_conflicts_are_contradictions():
    _, rules = load_corpus(STATUTES_DIR)
    kinds = {
        frozenset({c.rule_a.source_id, c.rule_b.source_id}): c.kind for c in find_candidates(rules)
    }
    assert kinds[frozenset({"us-ina-employment-noncriminalization", "az-sb1070-5c"})] == CONTRADICTION
    assert kinds[frozenset({"us-const-equal-protection-education", "tx-educ-code-21-031"})] == CONTRADICTION


def test_general_rule_is_not_flagged_against_its_own_exception():
    """The federal harboring prohibition carries `religious_volunteer != true`
    and its safe harbor carries `== true`. They partition the space, so no
    witness exists and no candidate is generated -- if the general rule were
    left unqualified, the statute would appear to contradict itself."""
    _, rules = load_corpus(STATUTES_DIR)
    by_id = {r.source_id: r for r in rules}
    general, exception = by_id["us-ina-harboring"], by_id["us-ina-harboring-religious-exemption"]
    assert general.action == "prohibited" and exception.action == "allowed"
    assert general.scope == exception.scope and general.activity == exception.activity
    assert _find_witness(general.condition, exception.condition) is None

    pairs = {frozenset({c.rule_a.source_id, c.rule_b.source_id}) for c in find_candidates(rules)}
    assert frozenset({"us-ina-harboring", "us-ina-harboring-religious-exemption"}) not in pairs


def test_categorical_boolean_conflict_has_a_bool_witness():
    """The harboring safe-harbor conflict is the corpus's categorical case."""
    _, rules = load_corpus(STATUTES_DIR)
    pair = next(
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id}
        == {"us-ina-harboring-religious-exemption", "az-sb1070-13-2929"}
    )
    assert pair.witness.lean_type == "Bool"
    assert pair.witness.value is True


def test_string_conditions_are_supported():
    a = rule("a", "student", "granting in-state tuition", ("basis", "==", "residence"), "allowed", "US Federal")
    b = rule("b", "student", "granting in-state tuition", (None, None, None), "prohibited", "Arizona State")
    candidates = find_candidates([a, b])
    assert len(candidates) == 1
    assert candidates[0].witness.lean_type == "String"
    assert candidates[0].witness.value == "residence"


def test_incompatible_string_equalities_are_not_a_candidate():
    a = rule("a", "student", "granting X", ("basis", "==", "residence"), "allowed", "US Federal")
    b = rule("b", "student", "granting X", ("basis", "==", "domicile"), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_mismatched_condition_types_are_not_a_candidate():
    """Same variable formalized as a number on one side and a string on the
    other is a formalization error, not a conflict -- excluded, not guessed at."""
    a = rule("a", "x", "some activity", ("basis", "==", 3), "allowed", "US Federal")
    b = rule("b", "x", "some activity", ("basis", "==", "three"), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_ordering_operator_on_categorical_value_is_rejected():
    for bad in ('basis > "residence"', "flag >= true"):
        try:
            Condition.from_text(bad)
        except ValueError:
            continue
        raise AssertionError(f"expected {bad!r} to be rejected")


def test_condition_round_trip_covers_every_kind():
    for text in ("always", "age >= 18", "religious_volunteer == true", 'basis != "residence"'):
        assert Condition.from_text(text).as_text() == text


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
    assert candidates[0].witness.value == 18


def test_non_overlapping_age_ranges_are_not_a_candidate():
    # "allowed if age >= 21" vs "prohibited if age < 21" partition perfectly -- no witness exists.
    a = rule("a", "adult", "possession of X", ("age", ">=", 21), "allowed", "Arizona State")
    b = rule("b", "minor", "possession of X", ("age", "<", 21), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_same_action_is_not_a_candidate():
    a = rule("a", "any person", "some activity", (None, None, None), "prohibited", "US Federal")
    b = rule("b", "some subset", "some activity", ("age", "<", 21), "prohibited", "Arizona State")
    assert find_candidates([a, b]) == []


def test_narrower_state_offense_does_not_match_broader_federal_one():
    """Regression for the South Carolina case that motivated exact matching.

    S.C. Act 69 § 4 criminalizes harboring *with intent to further unlawful
    entry* -- an extra element the `condition` field never captures. Its
    tokens are a strict superset of the federal phrase's, so the old subset
    branch matched them and the tool reported a conflict that may not exist.
    """
    federal_activity = "harboring or transporting an unlawfully present alien"
    state_activity = federal_activity + " with intent to further unlawful entry"
    assert not _same_activity(federal_activity, state_activity)

    a = rule("a", "any person", federal_activity, ("religious_volunteer", "==", True), "allowed", "US Federal")
    b = rule("b", "any person", state_activity, (None, None, None), "prohibited", "South Carolina State")
    assert find_candidates([a, b]) == []


def test_activity_matching_still_normalizes_case_punctuation_and_stopwords():
    """Exact means exact on the *normalized* token set, not on raw text."""
    assert _same_activity("Harboring an unlawfully present alien.", "harboring unlawfully present alien")
    assert _same_activity("seeking or engaging in unauthorized employment", "Seeking or engaging in unauthorized employment")


def test_near_miss_activity_keys_are_reported():
    """A singular/plural slip must be surfaced, not silently dropped."""
    a = rule("a", "x", "failing to carry alien registration document", (None, None, None), "prohibited", "US Federal")
    b = rule("b", "x", "failing to carry alien registration documents", (None, None, None), "allowed", "Arizona State")
    assert find_candidates([a, b]) == [], "keys differ, so the pair must not be compared"
    assert find_near_miss_activities([a, b]) == [
        ("failing to carry alien registration document", "failing to carry alien registration documents")
    ]


def test_genuinely_unrelated_activities_are_not_near_misses():
    a = rule("a", "x", "seeking or engaging in unauthorized employment", (None, None, None), "allowed", "US Federal")
    b = rule("b", "x", "failing to carry alien registration document", (None, None, None), "prohibited", "Arizona State")
    assert find_near_miss_activities([a, b]) == []


def test_corpus_has_no_near_miss_activity_keys():
    """Every real pairing in the corpus is an exact key match, so any near
    miss would be a typo hiding a conflict."""
    _, rules = load_corpus(STATUTES_DIR)
    assert find_near_miss_activities(rules) == []


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
