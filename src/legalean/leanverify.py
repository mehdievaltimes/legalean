"""Invoke the Lean 4 compiler to formally check generated conflict theorems.

This is the actual verification step: a candidate is only reported as a
confirmed conflict if `lake env lean <file>.lean` exits 0, meaning Lean's
kernel accepted a genuine proof of False from the two rules-as-hypotheses.
A non-zero exit is NOT an error in this tool -- it means Lean rejected the
claim (e.g. the conditions don't actually overlap), so the pair is simply
not reported.

Requires the Lean toolchain (elan + lake) to be installed and the lean/
Lake project to build (`lake build` in lean/) at least once first.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from .leangen import GeneratedFile


@dataclass
class VerificationResult:
    generated: GeneratedFile
    verified: bool
    stderr: str


def verify_all(generated_files: list[GeneratedFile], lean_project_dir: Path) -> list[VerificationResult]:
    results = []
    for gf in generated_files:
        proc = subprocess.run(
            ["lake", "env", "lean", str(gf.path.resolve())],
            cwd=lean_project_dir,
            capture_output=True,
            text=True,
        )
        results.append(VerificationResult(generated=gf, verified=proc.returncode == 0, stderr=proc.stderr.strip()))
    return results
