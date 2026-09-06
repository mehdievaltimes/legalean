---
id: tx-educ-code-21-031
jurisdiction: Texas State
citation: Tex. Educ. Code Ann. § 21.031 (Vernon Supp. 1981) (1975 revision); held unconstitutional in Plyler v. Doe, 457 U.S. 202 (1982)
subject: state or local school district
activity: denying free public education to an unlawfully present child
condition: age > 5
action: allowed
scope: Texas State
---

# Tex. Educ. Code § 21.031 — school enrollment limited to lawfully present children

## Excerpt

> All children who are citizens of the United States or legally admitted
> aliens and who are over the age of five years and under the age of 21
> years on the first day of September of any scholastic year shall be
> entitled to the benefits of the Available School Fund for that year. Every
> child in this state who is a citizen of the United States or a legally
> admitted alien and who is over the age of five years and not over the age
> of 21 years on the first day of September of the year in which admission
> is sought shall be permitted to attend the public free schools of the
> district.

## Formalization notes

The statute grants the entitlement *only* to citizens and legally admitted
aliens. The 1975 revision accordingly withheld state funds from districts
for educating children not "legally admitted," and authorized districts to
deny them enrollment — so as to an unlawfully present child the rule is
`allowed` (the district may deny), which is what collides with the
constitutional prohibition.

`condition: age > 5` comes straight from the statute's own school-age floor
("over the age of five years"). The upper bound ("not over the age of 21")
cannot be carried too — the model holds a single predicate — so the
formalization is the lower half of a real range.

This is the corpus's first conflict with a **numeric** condition on one
side, so its generated Lean proof discharges the age premise with `omega`
rather than `trivial`, instantiated at the witness `6` that `candidates.py`
computes.

## Status

**Held unconstitutional.** *Plyler v. Doe*, 457 U.S. 202 (1982) (Brennan,
J.), 5-4: denying undocumented school-age children the free public education
provided to citizen and lawfully present children violates the Equal
Protection Clause.

## Conflicts with

- [`us-const-equal-protection-education`](us-const-equal-protection-education.md)
