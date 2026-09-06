#!/usr/bin/env python3
"""End-to-end check of the Lean formal-verification layer: generate Lean
theorems from candidates and actually compile them with `lake env lean`.

No LLM/API calls. Requires the Lean toolchain (elan + lake) on PATH -- see
README. This is the one script in tests/ that shells out (to `lake`, not to
any network service), so it's kept separate from test_candidates_manual.py.

    python3 tests/test_lean_verification.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legalean.candidates import Candidate, Witness, find_candidates  # noqa: E402
from legalean.corpus import load_corpus  # noqa: E402
from legalean.leangen import generate_conflict_files  # noqa: E402
from legalean.leanverify import verify_all  # noqa: E402
from legalean.models import Condition, Rule, Statute  # noqa: E402

ROOT = Path(__file__).parent.parent
STATUTES_DIR = ROOT / "statutes"
LEAN_DIR = ROOT / "lean"
SCRATCH_DIR = LEAN_DIR / "Legalean" / "ConflictsTestScratch"


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


def require_lean() -> None:
    if shutil.which("lake") is None:
        print("SKIP: `lake` not found on PATH -- install the Lean toolchain (see README) to run this test.")
        sys.exit(0)
    proc = subprocess.run(["lake", "build"], cwd=LEAN_DIR, capture_output=True, text=True)
    if proc.returncode != 0:
        print("FAIL: `lake build` failed:\n" + proc.stdout + proc.stderr)
        sys.exit(1)


def test_corpus_conflicts_are_formally_verified():
    statutes, rules = load_corpus(STATUTES_DIR)
    statutes_by_id = {s.id: s for s in statutes}
    candidates = find_candidates(rules)
    assert len(candidates) == 6

    generated = generate_conflict_files(candidates, statutes_by_id, SCRATCH_DIR)
    results = verify_all(generated, LEAN_DIR)
    assert len(results) == 6
    for result in results:
        assert result.verified, f"Lean rejected a conflict expected to be provable: {result.stderr}"


def test_prohibited_required_proof_uses_the_second_axiom():
    """The Alabama school-status pair is prohibited/required, so its proof must
    close with prohibited_required_excl -- the axiom no other real pair reaches."""
    statutes, rules = load_corpus(STATUTES_DIR)
    statutes_by_id = {s.id: s for s in statutes}
    alabama = [
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id}
        == {"us-const-equal-protection-school-status-check", "al-hb56-28"}
    ]
    assert len(alabama) == 1
    generated = generate_conflict_files(alabama, statutes_by_id, SCRATCH_DIR)
    source = generated[0].path.read_text(encoding="utf-8")
    assert "prohibited_required_excl" in source
    assert "allowed_prohibited_excl" not in source
    assert verify_all(generated, LEAN_DIR)[0].verified


def test_numeric_condition_proof_uses_omega():
    """The Plyler/Texas pair carries `age > 5`, so its generated proof must
    discharge that premise with omega (not trivial) and still compile."""
    statutes, rules = load_corpus(STATUTES_DIR)
    statutes_by_id = {s.id: s for s in statutes}
    plyler = [
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id}
        == {"us-const-equal-protection-education", "tx-educ-code-21-031"}
    ]
    assert len(plyler) == 1
    generated = generate_conflict_files(plyler, statutes_by_id, SCRATCH_DIR)
    source = generated[0].path.read_text(encoding="utf-8")
    assert "x > 5" in source, "expected the numeric condition in the generated hypothesis"
    assert "by omega" in source, "expected omega to discharge the numeric premise"
    assert verify_all(generated, LEAN_DIR)[0].verified


def test_categorical_bool_proof_uses_decide():
    """The harboring safe-harbor conflict quantifies over Bool, so its proof
    must discharge the premise with `decide` and compile."""
    statutes, rules = load_corpus(STATUTES_DIR)
    statutes_by_id = {s.id: s for s in statutes}
    pair = [
        c
        for c in find_candidates(rules)
        if {c.rule_a.source_id, c.rule_b.source_id}
        == {"us-ina-harboring-religious-exemption", "az-sb1070-13-2929"}
    ]
    assert len(pair) == 1
    generated = generate_conflict_files(pair, statutes_by_id, SCRATCH_DIR)
    source = generated[0].path.read_text(encoding="utf-8")
    assert "∀ x : Bool" in source, "expected the Bool carrier type"
    assert "by decide" in source and "by omega" not in source
    assert verify_all(generated, LEAN_DIR)[0].verified


def test_string_conditions_compile_end_to_end():
    """No corpus rule uses a string condition yet, so prove the String path
    works by generating and compiling one."""
    a = rule("a", "student", "granting in-state tuition", ("basis", "==", "residence"), "allowed", "US Federal")
    b = rule("b", "student", "granting in-state tuition", ("basis", "!=", "domicile"), "prohibited", "Arizona State")
    candidates = find_candidates([a, b])
    assert len(candidates) == 1 and candidates[0].witness.lean_type == "String"
    statutes_by_id = {
        i: Statute(id=i, jurisdiction="test", citation=f"test-{i}", raw_text="test") for i in ("a", "b")
    }
    generated = generate_conflict_files(candidates, statutes_by_id, SCRATCH_DIR)
    source = generated[0].path.read_text(encoding="utf-8")
    assert '∀ x : String' in source and '"residence"' in source
    assert verify_all(generated, LEAN_DIR)[0].verified


def test_generated_header_pairs_each_citation_with_its_own_rule():
    """Regression: the exclusion axiom fixes hypothesis order, which need not match
    candidate order -- the header must not pair ruleA's citation with ruleB's rule."""
    statutes, rules = load_corpus(STATUTES_DIR)
    statutes_by_id = {s.id: s for s in statutes}
    candidates = find_candidates(rules)
    generated = generate_conflict_files(candidates, statutes_by_id, SCRATCH_DIR)

    assert generated, "expected at least one generated file to check"
    for gf in generated:
        lines = gf.path.read_text(encoding="utf-8").splitlines()
        for rule in (gf.candidate.rule_a, gf.candidate.rule_b):
            citation = statutes_by_id[rule.source_id].citation
            # The line describing this rule must be the one directly after its own
            # citation -- regardless of which binder (ruleA/ruleB) it became.
            citation_idx = next(
                (i for i, ln in enumerate(lines) if citation in ln and ln.startswith(("ruleA:", "ruleB:"))),
                None,
            )
            assert citation_idx is not None, f"{gf.path.name}: citation for {rule.source_id} not in header"
            description = lines[citation_idx + 1]
            expected = f"({rule.scope}) {rule.subject}: {rule.action} to {rule.activity}"
            assert expected in description, (
                f"{gf.path.name}: citation for {rule.source_id} is followed by {description!r}, "
                f"expected {expected!r}"
            )


def test_genuinely_non_overlapping_candidate_is_rejected_by_lean():
    # Bypass candidates.py's own overlap check (it wouldn't emit this pair) to confirm
    # Lean itself -- not just the Python heuristic -- refuses a false conflict claim.
    a = rule("a", "adult", "possession of X", ("age", ">=", 21), "allowed", "Arizona State")
    b = rule("b", "minor", "possession of X", ("age", "<", 21), "prohibited", "Arizona State")
    fake_candidate = Candidate(rule_a=a, rule_b=b, witness=Witness(21, "Int"))  # satisfies neither jointly
    statutes_by_id = {
        "a": Statute(id="a", jurisdiction="Arizona State", citation="test", raw_text="test"),
        "b": Statute(id="b", jurisdiction="Arizona State", citation="test", raw_text="test"),
    }
    generated = generate_conflict_files([fake_candidate], statutes_by_id, SCRATCH_DIR)
    results = verify_all(generated, LEAN_DIR)
    assert len(results) == 1
    assert not results[0].verified, "Lean should have rejected a witness that satisfies neither condition"


def test_false_categorical_witness_is_rejected_by_lean():
    """The categorical analogue of the numeric check above: `false` does not
    satisfy `x = true`, and `decide` must refuse to prove that it does --
    otherwise the guarantee would be hollow for categorical conditions."""
    a = rule("a", "s", "act", ("flag", "==", True), "allowed", "US Federal")
    b = rule("b", "s", "act", (None, None, None), "prohibited", "Arizona State")
    bad = Candidate(rule_a=a, rule_b=b, witness=Witness(False, "Bool"))
    statutes_by_id = {
        i: Statute(id=i, jurisdiction="test", citation=f"test-{i}", raw_text="test") for i in ("a", "b")
    }
    results = verify_all(generate_conflict_files([bad], statutes_by_id, SCRATCH_DIR), LEAN_DIR)
    assert not results[0].verified, "Lean should have rejected a witness that fails the condition"


def run_all():
    require_lean()
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
    shutil.rmtree(SCRATCH_DIR, ignore_errors=True)
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    run_all()
