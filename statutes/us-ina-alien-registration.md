---
id: us-ina-alien-registration
jurisdiction: US Federal
citation: 8 U.S.C. §§ 1304(e), 1306(a)
subject: alien eighteen years of age or older
activity: failing to carry alien registration document
condition: age >= 18
action: prohibited
scope: US Federal
---

# INA §§ 264(e), 266(a) — federal alien registration and carry requirement

## Excerpt

> Every alien, eighteen years of age and over, shall at all times carry with
> them and have in their personal possession any certificate of alien
> registration or alien registration receipt card issued to them; willful
> failure to do so is a misdemeanor punishable by a fine of not more than
> $100 or imprisonment of not more than thirty days, or both (§ 1304(e)).
> Separately, an alien required to apply for registration and to be
> fingerprinted who willfully fails or refuses to do so is guilty of a
> misdemeanor punishable by a fine of up to $1,000 or up to six months'
> imprisonment, or both (§ 1306(a)). Together these provisions form a
> comprehensive registration scheme that occupies the field.

## Formalization notes

The only numeric condition in the corpus: § 1304(e) applies by its terms to
aliens eighteen and over, so `condition: age >= 18`. If this rule ever
became half of a candidate conflict, the generated Lean theorem would
discharge the age side with `omega` rather than `trivial`.

The `activity` is the **carry** offense, which is § 1304(e); § 1306(a) is
the distinct failure-to-*register* offense, cited here because A.R.S.
§ 13-1509 keyed its own offense to violations of both, and because the two
together are what the Court treated as the occupied field.

## Status

Good law — and the *reason* the Arizona analogue fell. See the note in
[`az-sb1070-3`](az-sb1070-3.md) for why this tool does **not** flag that
pair, even though the Supreme Court struck the state provision down.

## Related

- [`az-sb1070-3`](az-sb1070-3.md) — preempted, but not by direct contradiction.
