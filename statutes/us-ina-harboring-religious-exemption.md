---
id: us-ina-harboring-religious-exemption
jurisdiction: US Federal
citation: 8 U.S.C. § 1324(a)(1)(C); relied on in Valle del Sol v. Whiting, 732 F.3d 1006 (9th Cir. 2013)
subject: religious denomination or its agents
activity: harboring or transporting an unlawfully present alien
condition: religious_volunteer == true
action: allowed
scope: US Federal
---

# INA § 274(a)(1)(C) — the religious-volunteer safe harbor

## Excerpt

> It is not a violation of the transporting or harboring clauses for a
> religious denomination having a bona fide nonprofit religious organization
> in the United States, or its agents or officers, to encourage, invite,
> call, allow, or enable an alien present in the United States to perform
> the vocation of a minister or missionary as a volunteer who is not
> compensated as an employee — notwithstanding room, board, travel, medical
> assistance and other basic living expenses — provided the minister or
> missionary has been a member of the denomination for at least one year.

## Formalization notes — the exception, finally formalized

`condition: religious_volunteer == true` is a **boolean categorical**
condition, which the tool now supports. `religious_volunteer` stands for the
whole conjunction the statute actually requires (bona fide nonprofit
denomination, unpaid volunteer, one year's membership, basic living support
only) — a single flag standing in for four conditions, which is a real
compression and is why the flag is named for the gist rather than any one
element.

The counterpart general rule
[`us-ina-harboring`](us-ina-harboring.md) now carries
`religious_volunteer != true`, so the two federal rules partition the space
rather than contradicting each other. That matters: without the `!=` the
tool would report the federal statute as conflicting with **its own
exception**, which is the classic failure mode of formalizing a general rule
and a carve-out as flat, unqualified propositions.

## Status

Good law.

## Conflicts with

- [`az-sb1070-13-2929`](az-sb1070-13-2929.md) — Arizona's harboring offense
  has no equivalent carve-out, so it reaches conduct Congress protected.
  This is the conflict the Ninth Circuit's analysis turned on, and it is now
  detected rather than documented as a miss.
