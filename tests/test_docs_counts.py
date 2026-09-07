#!/usr/bin/env python3
"""Fail if the docs drift from what the pipeline actually reports.

Every count that appears in README.md, docs/index.html or docs/social-card.html
is re-derived here from the corpus itself, so adding a statute cannot silently
leave a stale number on the public project page.

Pure stdlib, no Lean, no network -- the candidate counts come from the same
pre-filter check_conflicts.py uses. Lean can only ever *reject* candidates, so
these are the numbers the docs are allowed to claim.

    python3 tests/test_docs_counts.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from legalean.candidates import find_candidates  # noqa: E402
from legalean.corpus import load_corpus  # noqa: E402

ROOT = Path(__file__).parent.parent
WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
    8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen",
    14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
    19: "nineteen", 20: "twenty", 21: "twenty-one", 22: "twenty-two",
}


def word(n: int) -> str:
    if n not in WORDS:
        raise AssertionError(f"add {n} to WORDS in {__file__}")
    return WORDS[n]


def facts() -> dict:
    statutes, rules = load_corpus(ROOT / "statutes")
    candidates = find_candidates(rules)
    kinds = Counter(c.kind for c in candidates)
    return {
        "rules": len(rules),
        "candidates": len(candidates),
        "contradictions": kinds["contradiction"],
        "preemptions": kinds["preemption"],
        "jurisdictions": len({r.scope for r in rules}),
    }


def expect(haystack: str, needle: str, where: str, failures: list) -> None:
    """Assert `needle` appears verbatim, reporting the near miss if it doesn't."""
    if needle in haystack:
        return
    # Show what is actually there, to make the fix obvious.
    stem = needle.split()[0]
    near = [ln.strip() for ln in haystack.splitlines() if stem in ln][:2]
    failures.append(
        f"{where}: expected to find\n      {needle!r}\n"
        + ("    but found instead:\n" + "\n".join(f"      {n!r}" for n in near) if near else "    (no similar line found)")
    )


def main() -> None:
    f = facts()
    failures: list[str] = []

    readme = (ROOT / "README.md").read_text()
    page = (ROOT / "docs" / "index.html").read_text()
    card = (ROOT / "docs" / "social-card.html").read_text()

    # -- README ------------------------------------------------------------
    expect(
        readme,
        f"Expected output: {f['rules']} rules loaded, {f['candidates']} candidates checked, {f['candidates']} formally verified",
        "README expected-output line",
        failures,
    )
    expect(
        readme,
        f"({word(f['contradictions'])} contradictions and {word(f['preemptions'])} field preemptions)",
        "README conflict-kind breakdown",
        failures,
    )
    for phrase in re.findall(r"[A-Z]?[a-z]+ excerpts across [a-z]+ jurisdictions", readme):
        if phrase.lower() != f"{word(f['rules'])} excerpts across {word(f['jurisdictions'])} jurisdictions":
            failures.append(
                f"README corpus description: {phrase!r} should read "
                f"{word(f['rules'])} excerpts across {word(f['jurisdictions'])} jurisdictions"
            )

    # The pairings claim must match the rows actually in the table.
    rows = [ln for ln in readme.splitlines() if ln.startswith("| ") and "↔" in ln]
    pairings = len(rows)
    expect(readme, f"{word(pairings)} real pairings", "README pairings count", failures)
    table_preemptions = sum("**field preemption** (Lean-verified)" in r for r in rows)
    table_conflicts = sum("**conflict** (Lean-verified)" in r for r in rows)
    if table_preemptions != f["preemptions"]:
        failures.append(f"README table marks {table_preemptions} field preemptions; pipeline finds {f['preemptions']}")
    if table_conflicts != f["contradictions"]:
        failures.append(f"README table marks {table_conflicts} contradictions; pipeline finds {f['contradictions']}")

    # -- docs/index.html ---------------------------------------------------
    for value, label in (
        (f["rules"], "statutory excerpts, hand-formalized"),
        (f["candidates"], "conflicts proved by the Lean kernel"),
        (f["jurisdictions"], "jurisdictions: federal"),
    ):
        expect(page, f"<b>{value}</b><span>{label}", "project page stat tile", failures)
    expect(page, f"{f['contradictions']} of {f['candidates']} ·", "project page contradiction tag", failures)
    expect(page, f"{f['preemptions']} of {f['candidates']} ·", "project page preemption tag", failures)
    expect(
        page,
        f"{word(f['rules']).capitalize()} excerpts across {word(f['jurisdictions'])} jurisdictions, covering {word(pairings)} pairings",
        "project page results intro",
        failures,
    )
    expect(
        page,
        f"{f['rules']} rules loaded, {f['candidates']} candidates checked, {f['candidates']} formally verified conflicts — {word(f['contradictions'])} contradictions and {word(f['preemptions'])} field preemptions",
        "project page running-it paragraph",
        failures,
    )
    expect(
        page,
        f"{f['rules']} excerpts, {f['candidates']} machine-checked conflicts, {word(f['jurisdictions'])} jurisdictions.",
        "project page og:description",
        failures,
    )
    page_field = page.count('class="verdict v-field"')
    page_conflict = page.count('class="verdict v-conflict"')
    if page_field != f["preemptions"]:
        failures.append(f"project page table marks {page_field} field preemptions; pipeline finds {f['preemptions']}")
    if page_conflict != f["contradictions"]:
        failures.append(f"project page table marks {page_conflict} contradictions; pipeline finds {f['contradictions']}")

    # -- docs/social-card.html --------------------------------------------
    for value, label in (
        (f["rules"], "excerpts formalized"),
        (f["candidates"], "kernel-verified conflicts"),
        (f["preemptions"], "by field preemption"),
        (f["jurisdictions"], "jurisdictions"),
    ):
        expect(card, f"<b>{value}</b><span>{label}</span>", "social card stat", failures)

    # -- report ------------------------------------------------------------
    print(
        f"corpus: {f['rules']} rules, {f['candidates']} candidates "
        f"({f['contradictions']} contradictions + {f['preemptions']} preemptions), "
        f"{f['jurisdictions']} jurisdictions, {pairings} pairings documented"
    )
    if failures:
        print(f"\n{len(failures)} doc(s) out of date:\n")
        for msg in failures:
            print(f"  - {msg}\n")
        print("Update the text above, or re-render the social card, then re-run.")
        sys.exit(1)
    print("PASS: README, project page and social card all match the pipeline")


if __name__ == "__main__":
    main()
