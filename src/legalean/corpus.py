"""Load the statute corpus from human-authored markdown files.

Each file in `statutes/` is one excerpt: YAML-ish frontmatter carries the
formalization (the fields that become a `Rule`), and the `## Excerpt`
section carries the statutory text itself. Everything else in the file is
commentary for human readers and is ignored by the pipeline.

Markdown is the single source of truth -- there is no generated JSON cache
and no API call anywhere in this path. Frontmatter is parsed with a small
hand-rolled reader rather than PyYAML so the verification pipeline keeps
zero third-party Python dependencies; the accepted syntax is flat
`key: value` scalars, which is all the schema needs.
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import ACTIONS, Condition, Rule, Statute

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n(.*)\Z", re.DOTALL)
_EXCERPT_RE = re.compile(r"^##\s+Excerpt\s*$(.*?)(?=^##\s|\Z)", re.MULTILINE | re.DOTALL)

_REQUIRED_FIELDS = ("id", "jurisdiction", "citation", "subject", "activity", "condition", "action", "scope")


def _parse_frontmatter(block: str, path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for lineno, line in enumerate(block.splitlines(), start=2):
        if not line.strip():
            continue
        if ":" not in line:
            raise ValueError(f"{path}:{lineno}: frontmatter line is not 'key: value': {line!r}")
        key, value = line.split(":", 1)  # split once -- values contain colons (citations, quotes)
        fields[key.strip()] = value.strip()
    return fields


def _parse_excerpt(body: str, path: Path) -> str:
    match = _EXCERPT_RE.search(body)
    if not match:
        raise ValueError(f"{path}: no '## Excerpt' section found")
    lines = [re.sub(r"^>\s?", "", line).strip() for line in match.group(1).strip().splitlines()]
    text = " ".join(line for line in lines if line)
    if not text:
        raise ValueError(f"{path}: '## Excerpt' section is empty")
    return text


def load_statute_file(path: Path) -> tuple[Statute, Rule]:
    raw = path.read_text(encoding="utf-8")
    match = _FRONTMATTER_RE.match(raw)
    if not match:
        raise ValueError(f"{path}: file must start with a '---' frontmatter block")

    fields = _parse_frontmatter(match.group(1), path)
    missing = [f for f in _REQUIRED_FIELDS if f not in fields]
    if missing:
        raise ValueError(f"{path}: missing frontmatter field(s): {', '.join(missing)}")

    if fields["id"] != path.stem:
        raise ValueError(f"{path}: frontmatter id {fields['id']!r} does not match filename stem {path.stem!r}")
    if fields["action"] not in ACTIONS:
        raise ValueError(f"{path}: action must be one of {ACTIONS}, got {fields['action']!r}")

    statute = Statute(
        id=fields["id"],
        jurisdiction=fields["jurisdiction"],
        citation=fields["citation"],
        raw_text=_parse_excerpt(match.group(2), path),
    )
    exclusive_raw = fields.get("exclusive", "false").strip().lower()
    if exclusive_raw not in ("true", "false"):
        raise ValueError(f"{path}: exclusive must be 'true' or 'false', got {exclusive_raw!r}")

    rule = Rule(
        source_id=fields["id"],
        subject=fields["subject"],
        activity=fields["activity"],
        condition=Condition.from_text(fields["condition"]),
        action=fields["action"],
        scope=fields["scope"],
        exclusive=exclusive_raw == "true",
    )
    return statute, rule


def load_corpus(statutes_dir: str | Path) -> tuple[list[Statute], list[Rule]]:
    """Load every `*.md` in `statutes_dir`, sorted by filename for stable output."""
    paths = sorted(Path(statutes_dir).glob("*.md"))
    if not paths:
        raise ValueError(f"no statute markdown files found in {statutes_dir}")

    statutes: list[Statute] = []
    rules: list[Rule] = []
    for path in paths:
        statute, rule = load_statute_file(path)
        statutes.append(statute)
        rules.append(rule)
    return statutes, rules
