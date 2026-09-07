---
id: sc-act69-5
jurisdiction: South Carolina State
citation: S.C. Act No. 69 § 5 (2011) (S.B. 20); held field preempted in United States v. South Carolina, 720 F.3d 518 (4th Cir. 2013)
subject: alien eighteen years of age or older
activity: failing to carry alien registration document
condition: age >= 18
action: prohibited
scope: South Carolina State
---

# S.C. Act 69 § 5 — state failure-to-carry offense

## Excerpt

> It is unlawful for a person eighteen years of age or older to fail to carry
> in the person's possession any certificate of alien registration or alien
> registration receipt card issued to the person pursuant to 8 U.S.C. Section
> 1304 while the person is in this State. A violation is punishable by a fine
> of not more than $100, up to 30 days' imprisonment, or both.

## Formalization notes — the first pair with a condition on *both* sides

Every other rule displaced by an occupied field has been unconditional, so
the federal side's predicate did all the work and the witness came from one
condition alone. This provision carries its own age element — "eighteen years
of age or older" — which is the same threshold
[`us-ina-alien-registration`](us-ina-alien-registration.md) states, because
§ 5 is written by reference to 8 U.S.C. § 1304.

So both rules are numeric on `age`, and the witness comes from **intersecting
two intervals** rather than satisfying one: `age >= 18` ∩ `age >= 18` =
`[18, ∞)`, witness 18. The generated proof is correspondingly the first in
which *both* premises are discharged by `omega`:

```lean
theorem preemption_us_ina_alien_registration_vs_sc_act69_5
    (federal : (∀ x : Int, x ≥ 18 → ExclusivelyFederal (Activity x)))
    (state : (∀ x : Int, x ≥ 18 → Prohibited (Activity x))) :
    False :=
  field_preemption_excl (Activity 18) (federal 18 (by omega)) (Or.inr (Or.inl (state 18 (by omega))))
```

Until now that interval-intersection path existed only in the synthetic
tests. Note the age is a genuine element of the offense, not a formalization
convenience — Arizona's and Alabama's analogues omit it and are keyed
`always`, which is why they exercise the simpler path.

## Status

**Preliminarily enjoined.** *United States v. South Carolina*, 720 F.3d 518
(4th Cir. 2013): "we hold that Section 5 is field preempted by federal law,"
the Federal Government having occupied the field of alien registration. The
penalty — $100 and thirty days — mirrors federal § 1304(e) almost exactly,
and the provision was preempted anyway, which is the same lesson Alabama's
§ 10 carries.

This is Act 69's third appearance in the corpus, across its second field:
§ 4(B),(D) in harboring, § 6(B)(2) in document fraud, and § 5 here in
registration — three fields from one state act.

## Related

- [`us-ina-alien-registration`](us-ina-alien-registration.md) — occupies the field.
- [`az-sb1070-3`](az-sb1070-3.md), [`al-hb56-10`](al-hb56-10.md) — the same
  field, keyed `always`.
