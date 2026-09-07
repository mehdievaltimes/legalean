---
id: ga-hb87-7
jurisdiction: Georgia State
citation: O.C.G.A. §§ 16-11-200, 16-11-201, 16-11-202 (H.B. 87 § 7); preliminary injunction affirmed in Georgia Latino Alliance for Human Rights v. Governor of Georgia, 691 F.3d 1250 (11th Cir. 2012)
subject: any person
activity: harboring or transporting an unlawfully present alien while committing another criminal offense
condition: always
action: prohibited
scope: Georgia State
---

# H.B. 87 § 7 — Georgia's transporting, harboring and inducing offenses

## Excerpt

> A person who, while committing another criminal offense, knowingly and
> intentionally transports or moves an illegal alien in a motor vehicle for
> the purpose of furthering the illegal presence of the alien in the United
> States commits the offense of transporting or moving an illegal alien. A
> person who is acting in violation of another criminal offense and who
> knowingly conceals, harbors, or shields an illegal alien from detection in
> any place in this state commits the offense of concealing or harboring an
> illegal alien. A third offense covers inducing an illegal alien to enter
> the state. "Illegal alien" means a person verified by the federal
> government to be present in the United States in violation of federal
> immigration law.

## Formalization notes — the third state in the harboring field

Keyed narrowly, like [`sc-act69-4bd`](sc-act69-4bd.md) and unlike
[`az-sb1070-13-2929`](az-sb1070-13-2929.md): every offense in § 7 requires
the defendant to be committing or acting in violation of **another criminal
offense**, which is a real element the `condition` field does not capture.
So the key names the narrower act, and the consequence follows from the
matcher's two different activity semantics:

- **Field preemption fires** — a narrower offense is still inside the
  occupied field, so [`us-ina-harboring`](us-ina-harboring.md) displaces it.
- **No contradiction is claimed** against the religious safe harbor. Whether
  a volunteer minister could be "committing another criminal offense" is
  unasked and unanswered here.

### Why Arizona is keyed differently

A fair objection: A.R.S. § 13-2929 also has a predicate offense element
("a person who is in violation of a criminal offense"), yet it carries the
bare harboring key and therefore *does* produce a safe-harbor contradiction.
The difference is that the Ninth Circuit held Arizona's element **void for
vagueness** — "in violation of a criminal offense" was unintelligible — so
it does not function as a narrowing element, and the same court expressly
found the safe-harbor conflict real. Georgia's element is specific and
operative. Modeling a vague element as though it narrowed the offense would
discard a conflict a court actually found.

## Status

**Preliminarily enjoined.** *Georgia Latino Alliance for Human Rights v.
Governor of Georgia*, 691 F.3d 1250 (11th Cir. 2012) (No. 11-13044, filed
Aug. 20, 2012): "section 7 of H.B. 87 cannot be reconciled with the federal
immigration scheme or the individual provisions of the INA," and the panel
affirmed the preliminary injunction as to § 7 while **reversing** it as to
§ 8 (the status-verification provision, which is not in this corpus).

The field reasoning is the one *Valle del Sol* later quoted: the federal
government has expressed more than a "peripheral concern" with the entry,
movement and residence of aliens, and the breadth of those laws shows an
overwhelmingly dominant federal interest in the field.

## Related

- [`us-ina-harboring`](us-ina-harboring.md) — occupies the field.
- [`sc-act69-4bd`](sc-act69-4bd.md) — South Carolina's equivalent.
