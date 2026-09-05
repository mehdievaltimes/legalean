"""Jurisdiction/scope overlap rules.

Kept as an explicit, tiny lookup table rather than a general geography model --
this is a narrow demo over US Federal vs Arizona State law. A federal rule
with no carve-out applies everywhere within the US, including Arizona, so
"US Federal" and "Arizona State" are treated as overlapping scopes. (This is
also the constitutional premise -- U.S. Const. art. VI, cl. 2, the Supremacy
Clause -- behind why a conflicting state immigration law can be preempted at
all; see README.)
"""

from __future__ import annotations

# Symmetric containment/overlap pairs. Add more jurisdictions here if the
# sample data grows.
_OVERLAPPING_SCOPES = {
    frozenset({"US Federal", "Arizona State"}),
}


def scopes_overlap(scope_a: str, scope_b: str) -> bool:
    if scope_a == scope_b:
        return True
    return frozenset({scope_a, scope_b}) in _OVERLAPPING_SCOPES
