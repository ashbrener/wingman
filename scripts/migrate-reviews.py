#!/usr/bin/env python3
"""
Backfill ``.reviews/*.json`` from wingman_schema v1 → v2.

v1 (legacy, no ``wingman_schema_version`` field): flat shape with
``branch``, ``timestamp``, ``raw_review``, ``findings``, ``resolutions``,
and ``status``.

v2: adds ``wingman_schema_version: "2"``, top-level ``base`` (defaults
to ``"main"``), and a ``reviewer`` object extracted best-effort from
the ``raw_review`` prose. Fields not derivable from a v1 file are
``None`` (e.g. ``wall_seconds``, which v1 didn't capture).

Usage:
    python3 scripts/migrate-reviews.py [.reviews]

Idempotent — files already at v2 are left unchanged.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def _grep(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text, re.MULTILINE)
    return match.group(1).strip() if match else None


def _build_reviewer(raw: str) -> dict[str, object]:
    """
    Best-effort reviewer-metadata extraction from a v1 ``raw_review``.
    Fields not present in the codex banner default to ``None``.
    """
    return {
        "tool": "codex",
        "tool_version": _grep(raw, r"^OpenAI Codex (\S+)"),
        "model": _grep(raw, r"^model:\s*(.+)$"),
        "provider": _grep(raw, r"^provider:\s*(.+)$"),
        "reasoning_effort": _grep(raw, r"^reasoning effort:\s*(.+)$"),
        "session_id": _grep(raw, r"^session id:\s*(.+)$"),
        "wall_seconds": None,
    }


def migrate(path: Path) -> bool:
    """
    Migrate ``path`` from v1 to v2 in place. Returns True if a write
    happened, False if the file was already at v2.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("wingman_schema_version") == "2":
        return False
    raw = data.get("raw_review") or ""
    new = {
        "wingman_schema_version": "2",
        "branch": data.get("branch"),
        "timestamp": data.get("timestamp"),
        "base": data.get("base", "main"),
        "reviewer": _build_reviewer(raw),
        "raw_review": raw,
        "findings": data.get("findings", []),
        "resolutions": data.get("resolutions", []),
        "status": data.get("status", "needs_categorization"),
    }
    path.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    review_dir = Path(sys.argv[1] if len(sys.argv) > 1 else ".reviews")
    if not review_dir.is_dir():
        print(f"error: {review_dir} is not a directory", file=sys.stderr)
        return 1

    migrated = 0
    skipped = 0
    failed = 0
    for path in sorted(review_dir.glob("*.json")):
        try:
            if migrate(path):
                migrated += 1
                print(f"  migrated: {path}")
            else:
                skipped += 1
        except (OSError, json.JSONDecodeError) as exc:
            failed += 1
            print(f"  failed:   {path} — {exc}", file=sys.stderr)

    print(f"wingman migrate-reviews: {migrated} migrated, {skipped} already v2, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
