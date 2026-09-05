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
