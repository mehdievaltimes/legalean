# Legalean

A small end-to-end tool that extracts structured logical rules from real
statutory text and flags **structural** contradictions between them, using
plain Python -- no LLM in the loop for the comparison itself.

**Domain covered:** cannabis legality under the federal Controlled Substances
Act vs. New York's Marihuana Regulation and Taxation Act (MRTA). This pair
was picked because it has an unambiguous, well-documented conflict: federal
law prohibits marijuana possession outright, while NY law permits it for
adults 21+. A fifth excerpt (an indoor-smoking rule) is included as a
distractor to show the tool doesn't flag unrelated statutes just because
they share a jurisdiction.

## Framing

This is a **text-formalization + logical-conflict-detection** tool. It does
not, and is not meant to, decide which law is "correct," which one preempts
the other, or offer legal advice -- it surfaces structural contradictions
(one source says X is allowed, another says X is prohibited, for an
overlapping case) and leaves interpretation to the reader. See Limitations.

## Pipeline

```
data/statutes.json  --[LLM extraction, extract.py]-->  data/rules.json  --[pure Python, conflicts.py]-->  conflict report
```

1. **Ingestion** -- [`data/statutes.json`](data/statutes.json): each excerpt
   as `{id, jurisdiction, citation, raw_text}`.

2. **Extraction** ([`src/legalean/extract.py`](src/legalean/extract.py)) --
   one Anthropic API call per excerpt (via the `anthropic` Python SDK,
   `client.messages.create` with `output_config.format` set to a JSON
   schema, which constrains the model to return only valid JSON matching
   that schema -- no free-form parsing needed). Each excerpt becomes one
   rule object:

   ```jsonc
   {
     "subject": "person 21 years of age or older",
     "activity": "possession of cannabis",   // normalized topic, so rules about
                                              // the same real-world act can be
                                              // matched across different sources
     "condition": {"variable": "age", "operator": ">=", "value": 21},
     "action": "allowed",                    // "allowed" | "prohibited" | "required"
     "scope": "NY State"
   }
   ```

   `condition` is `{"variable": null, "operator": null, "value": null}` for
   an unconditional rule (applies to everyone, always) -- see the federal
   rules in the sample data. The full schema is documented as a plain dict,
   `RULE_JSON_SCHEMA`, in [`src/legalean/models.py`](src/legalean/models.py).

   The task spec asked for `{subject, condition, action, scope}`; `activity`
   was added because the sample set mixes statutes about different acts
   (possession vs. indoor smoking) -- without it, "same subject" string
   matching would either miss real conflicts or flag unrelated ones.

3. **Conflict detection** ([`src/legalean/conflicts.py`](src/legalean/conflicts.py))
   -- plain Python, **no LLM call**. Two rules are flagged when ALL of:
   - their `scope`s overlap (a tiny hardcoded hierarchy in
     [`scopes.py`](src/legalean/scopes.py) treats "US Federal" and "NY State"
     as overlapping, since federal law reaches into NY absent a carve-out),
   - their `activity` strings describe the same real-world act (normalized
     token overlap -- see `_same_activity`),
   - their `condition`s overlap (there's at least one case both rules speak
     to -- computed as numeric interval intersection for things like
     `age >= 21` vs `age < 21`, and an unconditional rule is treated as
     overlapping with anything, since it covers every sub-case),
   - their `action`s are logically contradictory (`allowed` vs.
     `prohibited`, or `prohibited` vs. `required` -- **not** `allowed` vs.
     `required`, since a mandatory act is trivially also a permitted one).

4. **Output** ([`check_conflicts.py`](check_conflicts.py)) -- a CLI that
   prints each conflicting pair: both citations, both extracted rules, and a
   one-line plain-English description of the contradiction. It renders no
   verdict on which rule is right.

## Running it

```bash
pip install -r requirements.txt
python3 check_conflicts.py
```

The repo ships with `data/rules.json` already populated (as if extraction
had already been run), so **the above works immediately with no API key** --
`check_conflicts.py` loads the cache instead of calling the LLM. Expected
output: 2 conflicts, both pitting the federal blanket prohibition against
NY's age-21 permission; the NY internal age split (`>=21` allowed / `<21`
prohibited) and the unrelated indoor-smoking rule correctly produce no
conflicts.

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

Other flags: `--statutes <path>` to point at a different excerpt file,
`--rules-cache <path>` to change where extracted rules are cached/read.

## Verifying the core logic without the API

```bash
python3 tests/test_conflicts_manual.py
```

A plain-assert script (not pytest -- kept minimal per project scope) that
checks `conflicts.py` against the shipped sample data plus a few hand-built
edge cases (the classic "allowed if age>=18 / prohibited if age<21" overlap,
a non-overlapping age partition, same-action non-conflicts, unrelated
activities, non-overlapping jurisdictions). Runs with no dependencies and no
network access.

## Limitations

- **Tiny, cherry-picked sample.** Five excerpts, one conflict pair. This is
  a proof of concept for the pipeline shape, not a survey of cannabis law.
- **LLM extraction noise.** The model may phrase `subject`/`activity`
  inconsistently across excerpts, miscategorize an exception as the general
  rule, or misread a condition. `_same_activity`'s token-overlap heuristic
  is a stopgap for matching topics across sources, not real NLP -- it will
  both over- and under-match on wording it hasn't seen. Every extracted
  rule should be spot-checked against its citation before being trusted.
- **Single-variable conditions only.** The condition model handles one
  numeric or categorical predicate per rule (`age >= 21`); it cannot
  represent compound conditions (`age >= 21 AND quantity <= 3oz`) or
  disjunctions.
- **Scope overlap is a hardcoded lookup**, not real knowledge of
  jurisdiction/preemption law -- it only knows the two jurisdictions in the
  sample data.
- **Not legal advice.** This tool reports structural contradictions between
  formalized excerpts of text. It does not know about preemption doctrine,
  severability, amendments, repeals, or how courts have actually resolved
  (or left unresolved) the federal/state cannabis conflict. Do not use its
  output to make a legal decision.

## Repo layout

```
check_conflicts.py         # CLI entry point
src/legalean/
  models.py                 # Statute/Rule/Condition dataclasses + RULE_JSON_SCHEMA
  extract.py                 # the only module that calls the Anthropic API
  conflicts.py               # pure-Python conflict detection
  scopes.py                   # jurisdiction overlap lookup
  storage.py                   # JSON load/save helpers
data/
  statutes.json              # input excerpts
  rules.json                  # cached extracted rules (checked in, so the CLI runs with no API key)
tests/
  test_conflicts_manual.py   # dependency-free assert script, no API calls
```
