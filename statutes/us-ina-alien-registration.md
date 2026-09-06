---
id: us-ina-alien-registration
jurisdiction: US Federal
citation: 8 U.S.C. §§ 1304(e), 1306(a)
subject: alien eighteen years of age or older
activity: failing to carry alien registration document
condition: age >= 18
action: prohibited
scope: US Federal
exclusive: true
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

## Formalization notes — `exclusive: true`

This is the corpus's only rule marked `exclusive`, meaning the federal
scheme occupies the whole field of alien registration and displaces *any*
state rule on the same activity, even one that agrees word for word. That is
what the Supreme Court held, and it is why this pair is now reported despite
both sides saying `prohibited`.

Be clear about what that flag is: unlike `subject`, `activity`, `condition`
and `action`, which are read off the statutory text, `exclusive` encodes a
**judicial holding**. Congress did not write "we occupy this field"; the
Court inferred it from the scheme's comprehensiveness. Marking a rule
exclusive is therefore an act of legal judgment being fed into the tool, not
a formalization of text — see README limitations.

## Status

Good law — and the *reason* the Arizona analogue fell.

## Related

- [`az-sb1070-3`](az-sb1070-3.md) — displaced by field preemption.
