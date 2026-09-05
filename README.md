# Legalean

A small end-to-end tool that extracts structured logical rules from real
statutory text and **formally verifies** logical contradictions between them
using Lean 4 -- not a Python heuristic, an actual machine-checked proof.

**Domain covered:** federal immigration law vs. Arizona's SB 1070, the
2010 state immigration-enforcement law partially struck down by the Supreme
Court in *Arizona v. United States*, 567 U.S. 387 (2012), for conflicting
with (being preempted by) federal law. This domain was picked because it has
a real, well-documented, citable contradiction of exactly the shape this
tool can formalize: federal law deliberately imposes no criminal penalty on
an unauthorized alien for seeking or engaging in unauthorized employment,
while SB 1070 § 5(C) made that same conduct a state crime -- the Court held
§ 5(C) preempted for exactly this reason. Two more excerpts (upheld E-Verify
requirements, and an alien-registration provision on both sides) are
included as documented non-conflicts -- see Limitations for why the tool
correctly stays silent on them, including one real case its model can't
capture.

## Framing

This is a **text-formalization + formal-logical-conflict-detection** tool.
It does not, and is not meant to, decide which law is "correct" or offer
legal advice -- it surfaces rule pairs that are *provably* inconsistent once
formalized, and leaves interpretation to the reader. A "conflict" reported
by this tool comes with a Lean proof term the kernel has type-checked, not
just a Python assertion.

## Pipeline

```
data/statutes.json --[LLM extraction]--> data/rules.json --[pure Python
pre-filter]--> candidates --[Lean codegen]--> lean/Legalean/Conflicts/*.lean
--[lake env lean, i.e. the Lean *compiler*]--> confirmed conflicts
```

1. **Ingestion** -- [`data/statutes.json`](data/statutes.json): each excerpt
   as `{id, jurisdiction, citation, raw_text}`.

2. **Extraction** ([`src/legalean/extract.py`](src/legalean/extract.py)) --
   one Anthropic API call per excerpt (via the `anthropic` Python SDK,
   `client.messages.create` with `output_config.format` set to a JSON
   schema, which constrains the model to return only valid JSON matching
   that schema). Each excerpt becomes one rule object:

   ```jsonc
   {
     "subject": "unauthorized alien",
     "activity": "seeking or engaging in unauthorized employment", // normalized
                                                                    // topic, so rules about the
                                                                    // same real-world act can be
                                                                    // matched across sources
     "condition": {"variable": null, "operator": null, "value": null}, // unconditional here;
                                                                        // {"variable": "age", "operator": ">=", "value": 21}
                                                                        // for a numeric gate
     "action": "allowed",                    // "allowed" | "prohibited" | "required"
     "scope": "US Federal"
   }
   ```

   The full schema is documented as a plain dict, `RULE_JSON_SCHEMA`, in
   [`src/legalean/models.py`](src/legalean/models.py). `activity` was added
   beyond the task spec's `{subject, condition, action, scope}` because the
   sample set mixes statutes about different acts (employment vs. carrying
   a registration document) -- without it, "same subject" string matching
   would either miss real conflicts or flag unrelated ones.

3. **Candidate pre-filtering** ([`src/legalean/candidates.py`](src/legalean/candidates.py))
   -- plain Python, **no LLM call, no Lean**. This does NOT decide whether
   two rules conflict -- it decides which pairs are even worth asking Lean
   about, by checking that ALL of:
   - `scope`s overlap (a tiny hardcoded lookup in
     [`scopes.py`](src/legalean/scopes.py) treats "US Federal" and "Arizona
     State" as overlapping, per the Supremacy Clause -- U.S. Const. art. VI,
     cl. 2 -- which is why a federal/state immigration conflict is even
     possible),
   - `activity` strings describe the same real-world act (normalized token
     overlap -- see `_same_activity`),
   - `action`s are logically contradictory (`allowed` vs. `prohibited`, or
     `prohibited` vs. `required` -- not `allowed` vs. `required`),
   - a concrete integer **witness** can be constructed that satisfies both
     rules' conditions (trivial when both are unconditional; interval
     arithmetic when both are numeric on the same variable). Conditions on
     different variables, or non-numeric conditions, are excluded here --
     see Limitations.

4. **Lean codegen** ([`src/legalean/leangen.py`](src/legalean/leangen.py))
   -- renders one self-contained Lean 4 file per candidate under
   `lean/Legalean/Conflicts/`, stating both rules as hypotheses over a
   shared opaque `Activity : Int → Prop` and claiming their combination
   is inconsistent (`False`), using the witness from step 3.

5. **Formal verification** ([`src/legalean/leanverify.py`](src/legalean/leanverify.py))
   -- runs `lake env lean` on each generated file. A pair is only reported
   as a **confirmed conflict** if Lean's kernel accepts the proof (exit 0).
   If the witness doesn't actually satisfy both conditions, or the action
   pair isn't really exclusive, Lean rejects the file and the pair is
   silently dropped -- this is the actual formal-verification guarantee,
   not a Python promise about it.

6. **Output** ([`check_conflicts.py`](check_conflicts.py)) -- a CLI that
   prints each Lean-confirmed conflict: both citations, both extracted
   rules, and a one-line plain-English description. No verdict on which
   rule is right.

### The Lean side: `lean/Legalean/Deontic.lean`

A tiny axiom set, not a big proof library:

```lean
axiom Allowed : Prop → Prop
axiom Prohibited : Prop → Prop
axiom Required : Prop → Prop

axiom allowed_prohibited_excl (p : Prop) : Allowed p → Prohibited p → False
axiom prohibited_required_excl (p : Prop) : Prohibited p → Required p → False
```

`Allowed`/`Prohibited`/`Required` are opaque; the only facts Lean knows about
them are the two exclusion axioms above (allowed/required is deliberately
*not* axiomatized as exclusive -- a mandatory act is trivially a permitted
one). A generated conflict file states each rule as `∀ x : Int, cond x →
Action (Activity x)`, instantiates both at the shared witness, and closes
with the matching exclusion axiom -- e.g. the real generated file for the
sample data's one conflict:

```lean
theorem conflict_us_ina_employment_noncriminalization_vs_az_sb1070_5c
    (ruleA : (∀ x : Int, True → Allowed (Activity x)))
    (ruleB : (∀ x : Int, True → Prohibited (Activity x))) :
    False :=
  allowed_prohibited_excl (Activity 0) (ruleA 0 trivial) (ruleB 0 trivial)
```

Numeric conditions (e.g. `age >= 21`) use Lean's built-in `omega` decision
procedure for linear integer arithmetic instead of `trivial` -- no mathlib
dependency, just core Lean 4.

## Running it

Requires Python 3.10+ and the Lean 4 toolchain (`elan`, which provides
`lean`/`lake`). If you don't have it:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh
```

Open a new shell afterward so `lake`/`lean` are on `PATH`, then:

```bash
pip install -r requirements.txt
python3 check_conflicts.py
```

The repo ships with `data/rules.json` already populated (as if extraction
had already been run) and `lean/` as a working Lake project, so **the above
works immediately with no Anthropic API key** -- only Lean needs to be
installed. `check_conflicts.py` runs `lake build` once (compiles the tiny
axioms module; no network access, no external Lean dependencies), then
generates and compiles one Lean file per structural candidate.

Expected output: 1 candidate checked, 1 formally verified conflict --
the federal-employment-noncriminalization rule vs. SB 1070 § 5(C). The
E-Verify rule and the (both-"prohibited") registration-document rules
correctly produce no candidates at all.

To re-run extraction from the raw text (e.g. after editing
`data/statutes.json`):

```bash
cp .env.example .env   # fill in ANTHROPIC_API_KEY
python3 check_conflicts.py --refresh
```

**Does my Claude.ai subscription cover this?** No -- a Claude Pro/Max chat
subscription and Anthropic API access are billed separately. `--refresh`
needs an API key from [console.anthropic.com](https://console.anthropic.com/settings/keys),
paid pay-as-you-go. Extracting 5 short excerpts costs a small fraction of a
cent regardless of which model you point it at. The default model is
`claude-opus-5`; set `LEGALEAN_MODEL=claude-sonnet-5` (or `claude-haiku-4-5`)
in your environment if you'd rather trade extraction quality for lower cost.

Other flags: `--statutes <path>` / `--rules-cache <path>` to point at
different files, `--keep-lean-files` to leave the generated
`lean/Legalean/Conflicts/*.lean` on disk for inspection instead of deleting
them after the run.

## Verifying the core logic without the API

```bash
python3 tests/test_candidates_manual.py    # pure Python, no API, no Lean/subprocess calls
python3 tests/test_lean_verification.py    # no API; shells out to `lake`/`lean` only
```

Plain-assert scripts (not pytest -- kept minimal per project scope), no
network access needed beyond the one-time Lean toolchain install. The first
checks `candidates.py`'s structural pre-filter against the shipped sample
data plus hand-built edge cases (the classic "allowed if age>=18 /
prohibited if age<21" overlap, a non-overlapping age partition, same-action
non-candidates, unrelated activities, non-overlapping jurisdictions,
mismatched condition variables). The second actually invokes the Lean
compiler: it confirms the sample data's one real conflict compiles (Lean
accepts the proof), and, separately, that a deliberately-constructed
non-overlapping witness is *rejected* by Lean -- i.e. Lean itself refuses a
false conflict claim, not just the Python heuristic.

## Limitations

- **Tiny, cherry-picked sample.** Five excerpts, one conflict. This is a
  proof of concept for the pipeline shape, not a survey of immigration law.
- **LLM extraction noise.** The model may phrase `subject`/`activity`
  inconsistently across excerpts or misread a condition. `_same_activity`'s
  token-overlap heuristic is a stopgap for matching topics across sources,
  not real NLP. Every extracted rule should be spot-checked against its
  citation before being trusted -- Lean verifies that the *formalized*
  rules are inconsistent, not that the formalization is faithful to the
  statute.
- **Field/obstacle preemption is NOT modeled -- a known false negative in
  the sample data.** `az-sb1070-3` (failing to carry an alien registration
  document) and `us-ina-alien-registration` (the federal registration/carry
  requirement) are both formalized as `prohibited`, so this tool's
  allowed-vs-prohibited model correctly finds no *direct* contradiction
  between them. But SB 1070 § 3 was *also* struck down in *Arizona v.
  United States* -- not because it contradicted federal law's substance,
  but because Congress's registration scheme was held to *occupy the
  field*, leaving no room for any state law on the same subject regardless
  of whether it agrees. That's a different, more common kind of immigration
  preemption than the deontic contradiction this tool checks for, and it
  would need a different rule field (e.g. an `exclusive_federal_domain`
  flag on the activity) and different Lean axioms to formalize. Left out of
  this MVP's scope deliberately rather than modeled inaccurately.
- **Single-variable numeric conditions only.** `age >= 21` works; compound
  conditions (`age >= 21 AND income < X`) or disjunctions aren't modeled,
  and conditions on different variables are excluded from candidates rather
  than guessed at (see `candidates.py`).
- **Scope overlap is a hardcoded lookup**, not real preemption/jurisdiction
  law -- it only knows the two jurisdictions in the sample data.
- **Not legal advice.** Formal verification here means "these two
  *formalized* rules are logically inconsistent," which is a narrower claim
  than "these two statutes conflict as a matter of law." It doesn't know
  about severability, amendments, repeals, standing, or how courts have
  actually resolved unrelated aspects of the underlying dispute. Do not use
  its output to make a legal decision.

## Repo layout

```
check_conflicts.py         # CLI entry point
src/legalean/
  models.py                 # Statute/Rule/Condition dataclasses + RULE_JSON_SCHEMA
  extract.py                 # the only module that calls the Anthropic API
  candidates.py               # pure-Python structural pre-filter (not the final verdict)
  leangen.py                   # renders Lean 4 theorem files from candidates
  leanverify.py                 # compiles them with `lake env lean`; the actual verdict
  scopes.py                       # jurisdiction overlap lookup
  storage.py                       # JSON load/save helpers
data/
  statutes.json              # input excerpts
  rules.json                  # cached extracted rules (checked in, so the CLI runs with no API key)
lean/                       # Lake project
  lean-toolchain              # pins the Lean 4 toolchain version (via elan)
  lakefile.toml                # Lake package config
  Legalean/Deontic.lean          # the deontic-logic axioms (Allowed/Prohibited/Required + exclusions)
  Legalean/Smoke.lean             # standing regression tests for the axiom system, built by `lake build`
  Legalean/Conflicts/               # generated per-run by check_conflicts.py (gitignored)
tests/
  test_candidates_manual.py  # dependency-free assert script, no API/Lean calls
  test_lean_verification.py   # assert script that shells out to `lake`/`lean`, no API calls
```
