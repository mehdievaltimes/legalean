---
id: us-fraudulent-immigration-documents
jurisdiction: US Federal
citation: 8 U.S.C. § 1324c; 18 U.S.C. § 1546; field held occupied in United States v. South Carolina, 720 F.3d 518 (4th Cir. 2013)
subject: any person
activity: possessing or using a fraudulent immigration document
condition: always
action: prohibited
scope: US Federal
exclusive: true
---

# INA § 274C and 18 U.S.C. § 1546 — the federal document-fraud scheme

## Excerpt

> It is unlawful to use, attempt to use, possess, obtain, accept, or receive
> any forged, counterfeit, altered, or falsely made document in order to
> satisfy a requirement of the immigration laws or to obtain a benefit under
> them; violations carry civil penalties per document and, for certain
> conduct, criminal ones. Separately, whoever knowingly forges, counterfeits,
> alters or falsely makes an immigrant or nonimmigrant visa, permit, border
> crossing card or alien registration receipt card — or utters, uses,
> possesses, obtains, accepts or receives any such document knowing it to be
> forged or unlawfully obtained — commits a federal crime punishable by up to
> ten years, and longer where terrorism or drug trafficking is facilitated.

## Formalization notes — the corpus's third occupied field

`exclusive: true`, making this the third field the corpus models, after alien
registration ([`us-ina-alien-registration`](us-ina-alien-registration.md)) and
harboring ([`us-ina-harboring`](us-ina-harboring.md)). Three different federal
rules, three different fields, one mechanism — the `exclusive` flag is not
special-cased to any of them.

Two statutes are cited together because the field is the *combination*: § 1324c
supplies the civil document-fraud scheme and § 1546 the criminal one, and it
was their joint breadth that the Fourth Circuit treated as leaving no room for
state supplementation.

The usual caveat applies with the usual force: `exclusive` records a judicial
inference, not statutory text. Congress did not write that it occupies this
field; the Fourth Circuit inferred it. This one rests on a single circuit.

## Status

Good law.

## Displaces

- [`sc-act69-6b2`](sc-act69-6b2.md) — South Carolina's false-identification
  offense, held field preempted on the strength of these provisions.
