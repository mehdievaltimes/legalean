/-!
Minimal deontic-logic axioms used to formally check whether two extracted
statutory rules are jointly inconsistent.

`Allowed`, `Prohibited`, and `Required` are opaque (uninterpreted) unary
predicates over `Prop`. Each generated conflict file (see
`Legalean/Conflicts/*.lean`, produced by `src/legalean/leangen.py`) applies
them to a single file-local placeholder proposition representing "the
regulated activity occurs in this case" -- their internal meaning doesn't
matter, only the exclusion axioms below do.

This mirrors the action-contradiction table used during Python extraction:
allowed/prohibited and prohibited/required are mutually exclusive, while
allowed/required are not (a mandatory act is trivially also a permitted one).
-/

axiom Allowed : Prop → Prop
axiom Prohibited : Prop → Prop
axiom Required : Prop → Prop

axiom allowed_prohibited_excl (p : Prop) : Allowed p → Prohibited p → False
axiom prohibited_required_excl (p : Prop) : Prohibited p → Required p → False

/-!
## Field preemption

A second, structurally different kind of conflict. The two axioms above say
that a single act cannot carry two incompatible deontic statuses. Field
preemption says something stronger and more unusual: that a regulatory field
belongs exclusively to one sovereign, so *any* rule of *any* deontic flavor
from another sovereign is incompatible with it -- even one that agrees.

`ExclusivelyFederal p` marks the field containing `p` as exclusively
occupied. The axiom then rules out every deontic status a competing rule
could carry, which is why its second premise is a disjunction rather than a
specific modality: the generated proof injects whatever the competing rule
actually says.

Note what is NOT modeled here: `Allowed`/`Prohibited`/`Required` carry no
jurisdiction, so nothing in Lean prevents this axiom from being instantiated
with two rules of the same sovereign (which would be nonsense -- a federal
scheme does not preempt itself). Jurisdictional eligibility is enforced in
`src/legalean/scopes.py` before a theorem is ever generated. Lean checks the
derivation; Python supplies the jurisdictional premise.
-/

axiom ExclusivelyFederal : Prop → Prop

axiom field_preemption_excl (p : Prop) :
    ExclusivelyFederal p → (Allowed p ∨ Prohibited p ∨ Required p) → False
