---
id: us-ina-harboring
jurisdiction: US Federal
citation: 8 U.S.C. § 1324(a)(1)(A)(ii)-(iii), (a)(1)(C)
subject: any person
activity: harboring or transporting an unlawfully present alien
condition: religious_volunteer != true
action: prohibited
scope: US Federal
exclusive: true
---

# INA § 274(a) — federal harboring and transporting offenses

## Excerpt

> Any person who, knowing or in reckless disregard of the fact that an alien
> has come to, entered, or remains in the United States in violation of law,
> transports or moves such alien within the United States in furtherance of
> that violation, or conceals, harbors, or shields such alien from
> detection, commits a federal felony. It is not a violation of those
> clauses for a religious denomination having a bona fide nonprofit
> religious organization in the United States, or its agents or officers, to
> encourage, invite, call, allow, or enable an alien present in the United
> States to perform the vocation of a minister or missionary as a volunteer
> who is not compensated as an employee — notwithstanding room, board,
> travel, medical assistance and other basic living expenses — provided the
> minister or missionary has been a member of the denomination for at least
> one year.

## Formalization notes — the exemption is now carried, not dropped

`condition: religious_volunteer != true` qualifies the general prohibition
so that it stops exactly where § 1324(a)(1)(C)'s safe harbor begins. The
carve-out itself lives in
[`us-ina-harboring-religious-exemption`](us-ina-harboring-religious-exemption.md).

Earlier versions of this corpus formalized this rule as an unconditional
`prohibited`, which silently swallowed the exemption and made the tool miss
the very conflict the Ninth Circuit relied on. Adding categorical conditions
fixed that. Two consequences worth noting:

1. The tool now **detects** the conflict with
   [`az-sb1070-13-2929`](az-sb1070-13-2929.md), because Arizona's offense has
   no matching carve-out.
2. This rule and its own exception are correctly **not** flagged against each
   other: `religious_volunteer != true` and `religious_volunteer == true`
   admit no common witness, so no candidate is generated. A general rule and
   its exception are disjoint, not contradictory — but only if the general
   rule is written to say so.

## `exclusive: true` — the second occupied field

Four circuits have held that Congress occupies the field of alien harboring
and transporting: the Ninth (*Valle del Sol v. Whiting*, 732 F.3d 1006, in a
section headed "§ 13-2929 is Field Preempted"), the Eleventh (*GLAHR v.
Governor of Georgia*, 691 F.3d 1250, 1264), the Fourth (*United States v.
South Carolina*, 720 F.3d 518, 531), and the Third (*Lozano v. City of
Hazleton*). The flag records that consensus.

It makes this the corpus's **second** occupied field, distinct from alien
registration — which is the point of marking it. The `exclusive` mechanism
is not special-cased to one field.

Note the consequence for [`az-sb1070-13-2929`](az-sb1070-13-2929.md): it now
appears in **two** findings on independent grounds — displaced by this rule's
field claim, and separately contradicting the religious safe harbor. That is
faithful to *Valle del Sol*, which held it field preempted **and** conflict
preempted in consecutive sections.

The same caveat as the registration flag applies with more force here: the
field claim is a judicial inference, not statutory text, and this one rests
on circuit consensus rather than a Supreme Court holding.

## Status

Good law.

## Related

- [`us-ina-harboring-religious-exemption`](us-ina-harboring-religious-exemption.md)
  — the carve-out.
- [`az-sb1070-13-2929`](az-sb1070-13-2929.md) — the state offense that
  ignores it, preliminarily enjoined as conflict preempted.
