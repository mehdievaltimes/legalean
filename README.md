# Legalean

[![CI](https://github.com/mehdievaltimes/legalean/actions/workflows/ci.yml/badge.svg)](https://github.com/mehdievaltimes/legalean/actions/workflows/ci.yml)
[![Lean 4](https://img.shields.io/badge/Lean-4-2E2E2E)](lean/lean-toolchain)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](#running-it)
[![dependencies: none](https://img.shields.io/badge/dependencies-none-4C9A2A)](requirements.txt)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**[Project page →](https://mehdievaltimes.github.io/legalean/)**

A small end-to-end tool that turns statutory text into structured logical
rules and **formally verifies** contradictions between them using Lean 4 --
not a Python heuristic, an actual machine-checked proof.

The corpus lives in [`statutes/`](statutes/) as human-readable markdown: one
file per excerpt, with the formalization in its frontmatter and the
reasoning behind it written out underneath. The verification pipeline is
stdlib-only Python plus Lean — **no API key, no network access, no
third-party Python packages.**

**Domain covered:** federal immigration law vs. Arizona's S.B. 1070, the
2010 state immigration-enforcement law partly struck down by the Supreme
Court in *Arizona v. United States*, 567 U.S. 387 (2012). Twelve excerpts
cover four real federal/state pairings, chosen so that every branch of the
tool's logic is exercised against actual law:

| Pairing | Actions | Tool says | Courts said |
|---|---|---|---|
| Federal non-criminalization of unauthorized work ↔ S.B. 1070 § 5(C) | allowed / prohibited | **conflict** (Lean-verified) | § 5(C) struck down |
| Federal officer-only warrantless arrest ↔ S.B. 1070 § 6 | prohibited / allowed | **conflict** (Lean-verified) | § 6 struck down |
| Federal voluntary E-Verify ↔ Legal Arizona Workers Act | allowed / required | compatible, no conflict | state law upheld (*Whiting*) |
| Federal status-check cooperation ↔ S.B. 1070 § 2(B) | allowed / required | compatible, no conflict | § 2(B) upheld on its face |
| Federal alien registration ↔ S.B. 1070 § 3 | prohibited / prohibited | nothing (false negative) | § 3 preempted — *field* preemption |
| Federal harboring ↔ A.R.S. § 13-2929 | prohibited / prohibited | nothing (false negative) | enjoined — *conflict* preemption |

The last two rows are the honest part, and they fail for two *different*
reasons. The registration pair is invisible because the tool cannot model
**field preemption** (a duplicate state law is still void when Congress
occupied the field). The harboring pair is invisible because the federal
rule's religious safe harbor — the very thing the Ninth Circuit's conflict
analysis turned on — was **dropped in formalization**. Both are kept in the
corpus rather than hidden. See Limitations.

## Framing

This is a **text-formalization + formal-logical-conflict-detection** tool.
It does not decide which law is "correct," which one prevails, or offer
legal advice — it surfaces rule pairs that are *provably* inconsistent once
formalized, and leaves interpretation to the reader. A conflict it reports
comes with a Lean proof term the kernel has type-checked, not just a Python
assertion. (Conflicting pairs are displayed with the enclosing jurisdiction
first purely for readability; that is not a statement about precedence.)

## Pipeline

```
statutes/*.md --[markdown parse]--> rules --[pure-Python pre-filter]-->
candidates --[Lean codegen]--> lean/Legalean/Conflicts/*.lean
--[lake env lean, i.e. the Lean compiler]--> confirmed conflicts
```

1. **Corpus** ([`statutes/`](statutes/), loaded by
   [`corpus.py`](src/legalean/corpus.py)) — each excerpt is a markdown file
   whose frontmatter carries the formalization and whose `## Excerpt`
   section carries the statutory text. Everything else in the file is
   commentary for human readers. Frontmatter is parsed with a small
   hand-rolled reader (not PyYAML) to keep the pipeline dependency-free:

   ```markdown
   ---
   id: az-sb1070-5c
   jurisdiction: Arizona State
   citation: Ariz. Rev. Stat. § 13-2928(C) (S.B. 1070 § 5(C))
   subject: unauthorized alien
   activity: seeking or engaging in unauthorized employment
   condition: always          # or a predicate, e.g. `age >= 18`
   action: prohibited         # allowed | prohibited | required
   scope: Arizona State
   ---
   ```

   `activity` is the join key: two rules are only compared if they describe
   the same real-world act. `condition` uses a compact syntax that
   round-trips through `Condition.from_text` / `as_text`.

2. **Candidate pre-filtering** ([`candidates.py`](src/legalean/candidates.py))
   — plain Python, no Lean. This does **not** decide whether two rules
   conflict; it decides which pairs are worth asking Lean about, requiring
   all of: overlapping `scope`s (per [`scopes.py`](src/legalean/scopes.py),
   where "US Federal" reaches into "Arizona State" — the Supremacy Clause
   premise, U.S. Const. art. VI, cl. 2); same `activity`; contradictory
   `action`s; and a constructible integer **witness** satisfying both
   conditions.

3. **Lean codegen** ([`leangen.py`](src/legalean/leangen.py)) — one
   self-contained Lean file per candidate, stating both rules as hypotheses
   over a shared opaque `Activity : Int → Prop` and claiming `False`.

4. **Formal verification** ([`leanverify.py`](src/legalean/leanverify.py))
   — runs `lake env lean` per file. A pair is reported **only** if Lean's
   kernel accepts the proof. If the witness doesn't really satisfy both
   conditions, Lean rejects the file and the pair is dropped. That is the
   actual guarantee, rather than a Python promise about one.

5. **Output** ([`check_conflicts.py`](check_conflicts.py)) — prints each
   Lean-confirmed conflict with both citations, both rules, and a one-line
   description.

### The Lean side

[`lean/Legalean/Deontic.lean`](lean/Legalean/Deontic.lean) is a tiny axiom
set, not a big proof library:

```lean
axiom Allowed : Prop → Prop
axiom Prohibited : Prop → Prop
axiom Required : Prop → Prop

axiom allowed_prohibited_excl (p : Prop) : Allowed p → Prohibited p → False
axiom prohibited_required_excl (p : Prop) : Prohibited p → Required p → False
```

The modalities are opaque; the only facts Lean knows are those two
exclusions. `allowed`/`required` is deliberately **not** exclusive — a
mandatory act is trivially a permitted one — and the corpus contains two
real pairs (E-Verify, § 2(B)) that depend on exactly that choice. A
generated proof instantiates both rules at the shared witness and closes
with the matching axiom:

```lean
theorem conflict_us_ina_employment_noncriminalization_vs_az_sb1070_5c
    (ruleA : (∀ x : Int, True → Allowed (Activity x)))
    (ruleB : (∀ x : Int, True → Prohibited (Activity x))) :
    False :=
  allowed_prohibited_excl (Activity 0) (ruleA 0 trivial) (ruleB 0 trivial)
```

Numeric conditions (e.g. `age >= 18`) discharge with core Lean's `omega`
decision procedure instead of `trivial` — no mathlib, just Lean 4 core.

## Running it

Requires Python 3.10+ and the Lean 4 toolchain (`elan`, providing
`lean`/`lake`). If you don't have it:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh
```

Open a new shell so `lake` is on `PATH`, then:

```bash
python3 check_conflicts.py
```

That's the whole setup — no `pip install` needed for the verification path.
It runs `lake build` once (compiles the axioms module; no network, no
external Lean dependencies), then generates and compiles one Lean file per
candidate.

Expected output: 12 rules loaded, 2 candidates checked, 2 formally verified
conflicts.

Flags: `--statutes <dir>` to point at a different corpus,
`--keep-lean-files` to leave the generated proofs in
`lean/Legalean/Conflicts/` for inspection instead of cleaning them up.

### Adding a statute

Write a new `statutes/<id>.md` by hand (copy an existing one — the
frontmatter fields are the whole contract, and `id` must match the
filename). Re-run `check_conflicts.py`; nothing else needs regenerating.

Optionally, [`src/legalean/extract.py`](src/legalean/extract.py) will draft
the frontmatter for you with an LLM. It is **not** part of the verification
pipeline and nothing imports it:

```bash
pip install anthropic          # the only third-party dependency, optional
export ANTHROPIC_API_KEY=...   # from console.anthropic.com
python3 -m legalean.extract excerpt.txt "US Federal" "8 U.S.C. § 1324a"
```

It prints proposed frontmatter to review and edit. Note a Claude.ai Pro/Max
chat subscription does **not** grant API access — that's billed separately,
pay-as-you-go. The committed corpus was formalized by hand, so this was
never run against it.

## Verifying the logic

```bash
python3 tests/test_candidates_manual.py    # pure Python: corpus parsing + pre-filter
python3 tests/test_lean_verification.py    # invokes the Lean compiler
```

Plain-assert scripts (not pytest — kept minimal per project scope), no
network access, no API calls. The first checks the corpus parses, that the
two conflicts are found, that the two compatible pairs and two
field-preemption pairs are correctly *not* flagged, and covers edge cases
(overlapping age gates, non-overlapping partitions, same-action pairs,
unrelated activities, disjoint jurisdictions, mismatched condition
variables). The second compiles generated proofs and asserts three things:
the corpus's real conflicts are accepted by Lean; a deliberately
non-overlapping witness is **rejected** by Lean (so the guarantee is real,
not decorative); and each generated file's header pairs every citation with
its own rule.

`lake build` in `lean/` also compiles
[`Legalean/Smoke.lean`](lean/Legalean/Smoke.lean), standing regression tests
for the axiom system itself.

## Limitations

- **Small, curated corpus.** Twelve excerpts, one statute per file, chosen
  to exercise the logic. Not a survey of immigration law.
- **Formalization is the weak link, and it's manual.** Lean verifies that
  the *formalized* rules are inconsistent — never that the formalization is
  faithful to the statute. Each file's "Formalization notes" section records
  where it compresses real doctrine (e.g. `allowed` standing in for "not
  criminally prohibited", or § 2(B)'s "reasonable suspicion" and "when
  practicable" qualifiers being dropped). Read them skeptically.
- **Field preemption is not modeled.** S.B. 1070 § 3 merely *duplicates* the
  federal registration offense, so there is no contradiction to find — yet
  the Supreme Court held it preempted because Congress occupied the field,
  leaving no room for a parallel state law even one that agrees. Modeling
  this needs a different rule field (e.g. `exclusive_federal_domain`) and
  new axioms. Left unmodeled deliberately rather than modeled inaccurately.
- **Dropped exceptions cause missed conflicts.** The federal harboring
  statute's religious safe harbor (8 U.S.C. § 1324(a)(1)(C)) is flattened
  away by formalizing that rule as an unconditional `prohibited`. That
  exemption is exactly what the Ninth Circuit's conflict-preemption analysis
  of A.R.S. § 13-2929 relied on, so the tool misses a conflict it is
  otherwise shaped to catch. Conflicts frequently live in the exceptions,
  and a single-predicate `condition` cannot hold them.
- **Single-variable conditions only.** `age >= 18` works; compound
  conditions and disjunctions don't. Conditions on different variables, or
  categorical ones, are excluded from candidates rather than guessed at.
- **Scope overlap is a hardcoded lookup**, not real jurisdiction law — it
  knows only the jurisdictions in the corpus.
- **Not legal advice.** "Formally verified" means these two *formalized*
  rules are logically inconsistent, which is a much narrower claim than
  "these two statutes conflict as a matter of law." The tool knows nothing
  of severability, amendment, repeal, standing, or remedy.

## Repo layout

```
check_conflicts.py           # CLI entry point
statutes/*.md                # the corpus: source of truth, one excerpt per file
src/legalean/
  models.py                  # Statute/Rule/Condition + condition text parsing
  corpus.py                  # markdown + frontmatter loader (stdlib only)
  candidates.py              # pure-Python structural pre-filter (not the verdict)
  leangen.py                 # renders Lean 4 theorems from candidates
  leanverify.py              # compiles them with `lake env lean`; the verdict
  scopes.py                  # jurisdiction overlap + display ordering
  extract.py                 # OPTIONAL LLM drafting helper; nothing imports it
lean/                        # Lake project
  lean-toolchain             # pins the Lean 4 toolchain (via elan)
  lakefile.toml
  Legalean/Deontic.lean      # the deontic axioms
  Legalean/Smoke.lean        # regression tests for the axiom system
  Legalean/Conflicts/        # generated per run (gitignored)
tests/
  test_candidates_manual.py  # stdlib only, no Lean, no API
  test_lean_verification.py  # shells out to `lake`/`lean`, no API
```
