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

**Domain covered:** federal immigration law and the Constitution vs. state
law — principally Arizona's S.B. 1070, partly struck down in *Arizona v.
United States*, 567 U.S. 387 (2012), plus Texas's school-enrollment statute
struck down in *Plyler v. Doe*, 457 U.S. 202 (1982), and Alabama's H.B. 56.
Nineteen excerpts across four jurisdictions cover eleven real pairings, chosen
so that every branch of the tool's logic is exercised against actual law:

| Pairing | Actions | Tool says | Courts said |
|---|---|---|---|
| Federal non-criminalization of unauthorized work ↔ S.B. 1070 § 5(C) | allowed / prohibited | **conflict** (Lean-verified) | § 5(C) struck down |
| *the same federal rule* ↔ Ala. H.B. 56 § 11(a) | allowed / prohibited | **conflict** (Lean-verified) | § 11(a) permanently enjoined |
| Federal officer-only warrantless arrest ↔ S.B. 1070 § 6 | prohibited / allowed | **conflict** (Lean-verified) | § 6 struck down |
| 14th Am. equal protection (*Plyler*) ↔ Tex. Educ. Code § 21.031 | prohibited / allowed | **conflict** (Lean-verified) | § 21.031 unconstitutional |
| 14th Am. equal protection (*HICA*) ↔ Ala. H.B. 56 § 28 | prohibited / **required** | **conflict** (Lean-verified) | § 28 permanently enjoined |
| Federal voluntary E-Verify ↔ Legal Arizona Workers Act | allowed / required | compatible, no conflict | state law upheld (*Whiting*) |
| Federal status-check cooperation ↔ S.B. 1070 § 2(B) | allowed / required | compatible, no conflict | § 2(B) upheld on its face |
| Federal alien registration ↔ S.B. 1070 § 3 | prohibited / prohibited | **field preemption** (Lean-verified) | § 3 preempted — *field* preemption |
| *the same federal rule* ↔ Ala. H.B. 56 § 10 | prohibited / prohibited | **field preemption** (Lean-verified) | § 10 permanently enjoined |
| Federal harboring safe harbor ↔ A.R.S. § 13-2929 | allowed / prohibited | **conflict** (Lean-verified) | enjoined — *conflict* preemption |
| Federal harboring field ↔ *the same* A.R.S. § 13-2929 | prohibited / prohibited | **field preemption** (Lean-verified) | enjoined — *field* preemption |

Note the registration row: **both rules say `prohibited`**, so there is no
deontic contradiction there at all, and it is still reported. That is field
preemption — the second kind of conflict the tool detects, described below.
Both it and the harboring row were documented false negatives earlier in
this project's history; each was retired by a capability rather than by
rewording the corpus.

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
   condition: always          # or `age >= 18`, `flag == true`, `basis == "x"`
   action: prohibited         # allowed | prohibited | required
   scope: Arizona State
   exclusive: false           # optional; true = this sovereign occupies the field
   ---
   ```

   `activity` is the join key, matched **exactly** on its normalized token
   set (lowercased, punctuation and stopwords dropped) — it is a key, not a
   similarity score. Keys that look alike but differ are reported as
   near misses rather than joined; see below. `condition` uses a compact
   syntax that round-trips through `Condition.from_text` / `as_text`.

2. **Candidate pre-filtering** ([`candidates.py`](src/legalean/candidates.py))
   — plain Python, no Lean. This does **not** decide whether two rules
   conflict; it decides which pairs are worth asking Lean about. Every
   candidate needs an identical `activity` key and a constructible
   **witness** (a concrete case both conditions cover). Beyond that there
   are two shapes: a **contradiction** needs overlapping `scope`s (per
   [`scopes.py`](src/legalean/scopes.py), where "US Federal" reaches into
   "Arizona State" — the Supremacy Clause premise, U.S. Const. art. VI,
   cl. 2) plus contradictory `action`s; a **field preemption** needs one
   rule marked `exclusive` whose scope *strictly encloses* the other's, and
   ignores actions entirely.

3. **Lean codegen** ([`leangen.py`](src/legalean/leangen.py)) — one
   self-contained Lean file per candidate, stating both rules as hypotheses
   over a shared opaque `Activity` and claiming `False`. The carrier type
   (`Int`/`Bool`/`String`) and the closing axiom depend on the candidate.

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

The modalities are opaque; the only facts Lean knows are these exclusions
plus the field-preemption axiom below. Both deontic exclusions are
load-bearing on real law: five conflicts close with
`allowed_prohibited_excl`, and the Alabama school-status pair closes with
`prohibited_required_excl`. Meanwhile `allowed`/`required` is deliberately
**not** exclusive — a mandatory act is trivially a permitted one — which is
why the E-Verify and § 2(B) pairs are correctly silent. Put together, the
corpus says a state may require what federal law merely permits, but not
what it forbids.

A generated proof instantiates both rules at the shared witness and closes
with the matching axiom:

```lean
theorem conflict_us_ina_employment_noncriminalization_vs_az_sb1070_5c
    (ruleA : (∀ x : Int, True → Allowed (Activity x)))
    (ruleB : (∀ x : Int, True → Prohibited (Activity x))) :
    False :=
  allowed_prohibited_excl (Activity 0) (ruleA 0 trivial) (ruleB 0 trivial)
```

Numeric conditions discharge with core Lean's `omega` decision procedure
instead of `trivial` — no mathlib, just Lean 4 core. The *Plyler* pair
exercises this on real law, because Tex. Educ. Code § 21.031 carried its own
school-age floor:

```lean
theorem conflict_us_const_equal_protection_education_vs_tx_educ_code_21_031
    (ruleA : (∀ x : Int, x > 5 → Allowed (Activity x)))
    (ruleB : (∀ x : Int, True → Prohibited (Activity x))) :
    False :=
  allowed_prohibited_excl (Activity 6) (ruleA 6 (by omega)) (ruleB 6 trivial)
```

`6` is the witness `candidates.py` computes for `age > 5`; Lean re-checks
that it really satisfies the premise rather than taking Python's word.

**Categorical conditions** (boolean and string) quantify over `Bool` or
`String` instead of `Int` and discharge with `decide`, still core Lean. This
is what lets the federal harboring safe harbor be formalized as
`religious_volunteer == true`:

```lean
private def Activity (_x : Bool) : Prop := True

theorem conflict_us_ina_harboring_religious_exemption_vs_az_sb1070_13_2929
    (ruleA : (∀ x : Bool, x = true → Allowed (Activity x)))
    (ruleB : (∀ x : Bool, True → Prohibited (Activity x))) :
    False :=
  allowed_prohibited_excl (Activity true) (ruleA true (by decide)) (ruleB true trivial)
```

The carrier type is fixed by the witness, so both rules in a pair must be
formalized at the same type; a variable given a number on one side and a
string on the other yields no candidate rather than a bogus one.

### Activity keys and near misses

Because `activity` is matched exactly, `check_conflicts.py` lints the corpus
for keys that are *similar but unequal* — the pairs the old fuzzy matcher
would have joined — and warns on stderr:

```
warning: 1 pair(s) of activity keys look alike but are not equal, so the rules
carrying them will NOT be compared:
  - 'failing to carry alien registration document'
    'failing to carry alien registration documents'
  Unify them if they name the same act, or reword them if they don't.
```

Either they name one act and should be unified so the conflict is found, or
they name two and should be reworded so nobody unifies them. A similarity
threshold cannot tell those apart; a human can.

### Field preemption — the other kind of conflict

The exclusions above say a single act cannot carry two incompatible deontic
statuses. Field preemption says something different and stronger: a
regulatory field belongs exclusively to one sovereign, so *any* rule from
another sovereign in that field collides with it — **even one that agrees**.
That is why the second premise is a disjunction over all three modalities:

```lean
axiom ExclusivelyFederal : Prop → Prop

axiom field_preemption_excl (p : Prop) :
    ExclusivelyFederal p → (Allowed p ∨ Prohibited p ∨ Required p) → False
```

A rule opts in with `exclusive: true` in its frontmatter. The generated
proof states the displaced rule with its *actual* modality and injects it
into the disjunction, so the theorem is about the real rule rather than a
paraphrase:

```lean
theorem preemption_us_ina_alien_registration_vs_az_sb1070_3
    (federal : (∀ x : Int, x ≥ 18 → ExclusivelyFederal (Activity x)))
    (state : (∀ x : Int, True → Prohibited (Activity x))) :
    False :=
  field_preemption_excl (Activity 18) (federal 18 (by omega)) (Or.inr (Or.inl (state 18 trivial)))
```

Both rules there say `prohibited` — they agree completely — and the pair is
still a conflict. Alabama's § 10 goes further: it is *defined* by reference
to violations of §§ 1304(e) and 1306(a), so it could hardly agree with
federal law more closely, and the Eleventh Circuit held it preempted anyway
because "even complementary state regulation is impermissible." One
`exclusive` flag displaces parallel offences in both states at once.

Two fields are occupied in the corpus — alien registration and alien
harboring — by different federal rules, so the mechanism is not special-cased
to one. One provision, A.R.S. § 13-2929, is caught **twice on independent
grounds**: displaced by the federal harboring field claim, and separately
contradicting the religious safe harbor. That is how the Ninth Circuit
decided it, holding the section field preempted and conflict preempted in
consecutive sections. Two things constrain it: the federal rule's own condition
must still hold at the witness (`omega` checks `18 ≥ 18`), and the scope
relation must be *strict*, so a sovereign never preempts itself and no state
preempts another. Where a pair would qualify as both a contradiction and a
preemption, only the preemption is reported — it is dispositive regardless
of content, so the second finding would be noise.

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

Expected output: 19 rules loaded, 9 candidates checked, 9 formally verified
conflicts (six contradictions and three field preemptions).

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

- **Small, curated corpus.** Nineteen excerpts across four jurisdictions,
  one provision per file, chosen to exercise the logic. Not a survey of
  immigration law.
- **Constitutional rules fit the schema worst.** *Plyler*'s rule is a
  standard applied to a state's justification ("unless it furthers some
  substantial state interest"), not a flat ban. Encoding it as an
  unconditional `prohibited` drops that escape hatch and makes the rule look
  more absolute than it is — a simplification running opposite to the
  harboring one below, which makes a rule look narrower than it is.
- **Formalization is the weak link, and it's manual.** Lean verifies that
  the *formalized* rules are inconsistent — never that the formalization is
  faithful to the statute. Each file's "Formalization notes" section records
  where it compresses real doctrine (e.g. `allowed` standing in for "not
  criminally prohibited", or § 2(B)'s "reasonable suspicion" and "when
  practicable" qualifiers being dropped). Read them skeptically.
- **`exclusive: true` is a judicial holding, not statutory text — the most
  editorial input in the corpus.** Every other frontmatter field is read off
  the excerpt. Congress does not write "we occupy this field"; courts infer
  it from a scheme's comprehensiveness. So marking a rule exclusive feeds a
  legal conclusion into the tool and then derives consequences from it. The
  derivation is machine-checked; the premise is a judgment call, and a wrong
  one propagates silently. Exactly one corpus rule carries the flag, and a
  test pins that.
- **Jurisdiction is not formalized in Lean.** `Allowed`/`Prohibited`/
  `Required`/`ExclusivelyFederal` carry no scope, so nothing in the Lean
  encoding knows federal law outranks state law, or that two states are
  unrelated. `scopes.py` decides which pairs are eligible *before* a theorem
  is generated. Lean verifies the deontic and arithmetic core; Python
  supplies the jurisdictional premises. "Formally verified" should be read
  against that boundary.
- **Preemption is asserted per-rule, not inferred.** The tool cannot look at
  a federal scheme and conclude it occupies a field; a human decides. It also
  models only field preemption, not conflict or obstacle preemption as
  doctrines — those surface here only when they happen to coincide with a
  deontic contradiction, as with the harboring pair.
- **Single-variable conditions only.** `age >= 18` works; compound
  conditions and disjunctions don't. Conditions on different variables, or
  categorical ones, are excluded from candidates rather than guessed at.
- **Scope overlap is a hardcoded lookup**, not real jurisdiction law — it
  knows only the jurisdictions in the corpus.
- **`activity` is an exact key, so the corpus must be internally
  consistent.** Two rules about the same act that spell it differently will
  not be compared. That is deliberate — the previous fuzzy matcher accepted
  a subset relation, which meant a *narrower* state offense (harboring "with
  intent to further unlawful entry") matched a broader federal one, and the
  tool then reasoned as though the state rule reached every case the federal
  rule did. The extra element lives in the activity phrase, which the
  `condition` field never captures, so the pairing could manufacture a
  conflict. Exact matching trades that for a different risk — a typo
  silently hiding a real conflict — which is why near misses are reported
  loudly on stderr instead of being resolved by a threshold.
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
