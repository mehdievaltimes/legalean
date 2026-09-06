import Legalean.Deontic

/-!
Standing regression tests for the axiom system + witness/omega machinery
that `src/legalean/leangen.py` relies on when generating conflict proofs.
Compiled every `lake build` -- if these ever fail to typecheck, codegen is
producing something the underlying logic can no longer support.
-/

private def Activity (_x : Int) : Prop := True

/-- Two unconditional rules with contradictory actions must be inconsistent. -/
theorem smoke_unconditional_conflict
    (ruleA : ∀ x : Int, True → Allowed (Activity x))
    (ruleB : ∀ x : Int, True → Prohibited (Activity x)) :
    False :=
  allowed_prohibited_excl (Activity 0) (ruleA 0 trivial) (ruleB 0 trivial)

/-- Overlapping numeric ranges (18 satisfies both age>=18 and age<21) must be inconsistent. -/
theorem smoke_numeric_overlap_conflict
    (ruleA : ∀ x : Int, x ≥ 18 → Allowed (Activity x))
    (ruleB : ∀ x : Int, x < 21 → Prohibited (Activity x)) :
    False :=
  allowed_prohibited_excl (Activity 18) (ruleA 18 (by omega)) (ruleB 18 (by omega))

/-- prohibited/required is exclusive too (allowed/required is deliberately NOT). -/
theorem smoke_prohibited_required_conflict
    (ruleA : ∀ x : Int, True → Prohibited (Activity x))
    (ruleB : ∀ x : Int, True → Required (Activity x)) :
    False :=
  prohibited_required_excl (Activity 0) (ruleA 0 trivial) (ruleB 0 trivial)

/-- Field preemption bites regardless of what the competing rule says -- here
    the competing rule *agrees* with the federal one, and it is still ruled out. -/
theorem smoke_field_preemption_same_action
    (federal : ∀ x : Int, True → ExclusivelyFederal (Activity x))
    (state : ∀ x : Int, True → Prohibited (Activity x)) :
    False :=
  field_preemption_excl (Activity 0) (federal 0 trivial) (Or.inr (Or.inl (state 0 trivial)))

/-- ...and it reaches an `allowed` or `required` state rule just the same. -/
theorem smoke_field_preemption_allowed
    (federal : ∀ x : Int, x ≥ 18 → ExclusivelyFederal (Activity x))
    (state : ∀ x : Int, True → Allowed (Activity x)) :
    False :=
  field_preemption_excl (Activity 18) (federal 18 (by omega)) (Or.inl (state 18 trivial))
