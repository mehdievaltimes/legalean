"""Jurisdiction/scope overlap rules.

Kept as an explicit, tiny lookup table rather than a general geography model --
this is a narrow demo over US Federal vs NY State law. A federal rule with no
carve-out applies everywhere within the US, including NY, so "US Federal" and
"NY State" are treated as overlapping scopes.
"""

from __future__ import annotations

# Symmetric containment/overlap pairs. Add more jurisdictions here if the
# sample data grows.
_OVERLAPPING_SCOPES = {
    frozenset({"US Federal", "NY State"}),
}


def scopes_overlap(scope_a: str, scope_b: str) -> bool:
    if scope_a == scope_b:
        return True
    return frozenset({scope_a, scope_b}) in _OVERLAPPING_SCOPES
