---
id: sc-act69-4bd
jurisdiction: South Carolina State
citation: S.C. Act No. 69 § 4(B), (D) (2011) (S.B. 20); held field preempted in United States v. South Carolina, 720 F.3d 518, 531 (4th Cir. 2013)
subject: any person
activity: harboring or transporting an unlawfully present alien with intent to further unlawful entry
condition: always
action: prohibited
scope: South Carolina State
---

# S.C. Act 69 § 4(B), (D) — state harboring and transporting felonies

## Excerpt

> It is a felony for a person knowingly to transport or attempt to transport
> an unlawfully present person within the state with intent to further that
> person's unlawful entry or to avoid detection, or knowingly to conceal,
> harbor, or shelter an unlawfully present person from detection with the
> same intent.

## Formalization notes — a narrower offense, deliberately keyed as one

The `activity` here is **not** the bare harboring key that
[`us-ina-harboring`](us-ina-harboring.md) and
[`az-sb1070-13-2929`](az-sb1070-13-2929.md) share. South Carolina's offense
carries an extra element — the specific intent to further unlawful entry or
avoid detection — so it names a strictly narrower act, and the key says so.

That distinction decides which findings this file produces, and it is the
reason this statute could not be added until the matcher was fixed:

- **Field preemption fires.** A narrower offense is still inside the occupied
  field, which is the whole point of occupying one, so
  `us-ina-harboring`'s `exclusive: true` displaces it.
- **A contradiction does not.** Against the religious safe harbor in
  [`us-ina-harboring-religious-exemption`](us-ina-harboring-religious-exemption.md),
  the tool stays silent — correctly. Whether an unpaid volunteer minister
  could ever satisfy this statute's specific-intent element is exactly the
  unverified question, and it is not answered here.

Under the old fuzzy matcher this file produced *both* findings, the second
resting on an assumption nobody had checked. That is why it was left out of
the corpus when the harboring field was first added.

## Status

**Preliminarily enjoined.** *United States v. South Carolina*, 720 F.3d 518
(4th Cir. 2013) affirmed the district court's preliminary injunction,
holding §§ 4(B) and (D) field preempted — "the vast array of federal laws
and regulations on this subject is so pervasive that Congress left no room
for the States to supplement it" — and separately conflict preempted.

The citation carries no S.C. Code section because the opinion identifies
these provisions only as sections of Act 69; none is invented here.

## Related

- [`us-ina-harboring`](us-ina-harboring.md) — occupies the field.
- [`az-sb1070-13-2929`](az-sb1070-13-2929.md) — Arizona's broader counterpart.
