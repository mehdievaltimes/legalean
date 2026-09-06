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
    frozenset({"US Federal", "Texas State"}),
    frozenset({"US Federal", "Alabama State"}),
}


def scopes_overlap(scope_a: str, scope_b: str) -> bool:
    if scope_a == scope_b:
        return True
    return frozenset({scope_a, scope_b}) in _OVERLAPPING_SCOPES


# Scopes that geographically enclose others, broadest first. Used ONLY to
# order a conflicting pair for display and for stable theorem naming -- it is
# not a statement about which rule prevails. This tool reports structural
# contradictions and takes no position on precedence or preemption.
_ENCLOSING_ORDER = ("US Federal",)


def enclosing_first(scope_a: str, scope_b: str) -> bool:
    """True if scope_a should be presented before scope_b."""
    rank_a = _ENCLOSING_ORDER.index(scope_a) if scope_a in _ENCLOSING_ORDER else len(_ENCLOSING_ORDER)
    rank_b = _ENCLOSING_ORDER.index(scope_b) if scope_b in _ENCLOSING_ORDER else len(_ENCLOSING_ORDER)
    return rank_a <= rank_b
