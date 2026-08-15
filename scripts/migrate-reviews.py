#!/usr/bin/env python3
"""
Backfill ``.reviews/*.json`` from wingman_schema v1 → v2.

v1 (legacy, no ``wingman_schema_version`` field): flat shape with
``branch``, ``timestamp``, ``raw_review``, ``findings``, ``resolutions``,
and ``status``.

v4: adds ``parsed_findings`` — the findings parsed from the reviewer's
output at emit time (spec 002). Empty on a migrated file means "written
before parsing existed", NOT "clean"; fall back to ``raw_review`` there.

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
import subprocess
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


def _find_hook(review_dir: Path) -> Path | None:
    """The installed hook for the repo owning ``review_dir``.

    The parser is single-sourced in the hook, so backfill reads it from the
    installed copy rather than carrying a second implementation that could
    drift from the one that wrote the artifacts.
    """
    for base in (review_dir.resolve().parent, Path.cwd()):
        found = _hook_in_repo(base)
        if found is not None:
            return found
    return None


def _hook_in_repo(repo: Path) -> Path | None:
    """The installed pre-push hook for the repo containing ``repo``, if any."""
    try:
        top = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False,
        )
        if top.returncode == 0:
            repo = Path(top.stdout.strip())
        hp = subprocess.run(
            ["git", "-C", str(repo), "config", "core.hooksPath"],
            capture_output=True, text=True, check=False,
        )
        hooks_dir = Path(hp.stdout.strip()) if hp.returncode == 0 and hp.stdout.strip() else None
    except OSError:
        hooks_dir = None
    candidates = []
    if hooks_dir is not None:
        candidates.append(hooks_dir if hooks_dir.is_absolute() else repo / hooks_dir)
    candidates.append(repo / ".git" / "hooks")
    for d in candidates:
        candidate = d / "pre-push"
        if candidate.is_file():
            return candidate
    return None


def _load_parser(hook: Path):
    """Extract the anchored parser block from the hook and exec it."""
    text = hook.read_text(errors="replace")
    begin = "# --- BEGIN finding parser (verified by scripts/verify-parser.py) ---"
    end = "# --- END finding parser ---"
    if text.count(begin) != 1 or text.count(end) != 1:
        return None  # pre-v5 hook: nothing to backfill with
    ns: dict = {"re": re}
    try:
        exec(text.split(begin, 1)[1].split(end, 1)[0], ns)  # noqa: S102
    except Exception:  # pragma: no cover - a malformed hook must never abort a migration
        return None
    return ns if "_parse_findings" in ns and "_count_pri" in ns else None


def _backfill(data: dict, ns) -> int:
    """Populate parsed_findings + counts from the raw output already captured.

    The reviewer's output was recorded correctly all along — only the parsing
    was blind — so migrating is a re-read, not a re-review. Returns how many
    findings were recovered. Every other field is left untouched.
    """
    raw = data.get("raw_review") or ""
    parsed = ns["_parse_findings"](raw)
    data["parsed_findings"] = parsed
    conv = data.get("convergence")
    if isinstance(conv, dict):
        for tag in ("P1", "P2", "P3"):
            native = len([f for f in parsed if f["priority"] == tag])
            conv[f"p{tag[1]}_count"] = max(native, ns["_count_pri"](raw, tag))
        if conv.get("p1_count") or conv.get("p2_count"):
            # A round with findings has not converged, whatever it claimed.
            conv["stop_rule_met"] = False
    return len(parsed)


def _add_parsed_findings(data: dict) -> bool:
    """v3 → v4: add the ``parsed_findings`` array (spec 002).

    An EMPTY array on a migrated file is truthful, not a claim of cleanliness:
    it means the artifact was written before findings were parsed at emit
    time. Readers must fall back to ``raw_review`` for pre-v4 files — never
    conclude "no findings" from an empty ``parsed_findings`` on an old
    artifact.
    """
    if data.get("wingman_schema_version") == "4":
        return False
    data.setdefault("parsed_findings", [])
    data["wingman_schema_version"] = "4"
    return True


def migrate(path: Path, parser_ns=None, dry_run: bool = False) -> bool:
    """
    Migrate ``path`` in place: v1 → v2 (reshape), then any newer schema step.
    Returns True if a write happened.
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("wingman_schema_version") in {"2", "3", "4"} and parser_ns is not None:
        # Backfill (FR-010a): the raw output was captured correctly all along,
        # so re-read it rather than stubbing an empty array. Re-runnable: a
        # second pass parses the same raw to the same result.
        before = json.dumps(data, sort_keys=True)
        recovered = _backfill(data, parser_ns)
        data["wingman_schema_version"] = "4"
        if json.dumps(data, sort_keys=True) == before:
            return False
        if not dry_run:
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        if recovered:
            print(f"    ↳ recovered {recovered} finding(s) from {data.get('branch')}")
        return True
    if data.get("wingman_schema_version") in {"2", "3"}:
        # Already reshaped — only the additive newer steps apply. Every other
        # field is left exactly as written (v3's ci_status / convergence /
        # exemptions / notices survive untouched).
        if not _add_parsed_findings(data):
            return False
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return True
    if data.get("wingman_schema_version") == "4":
        return False
    raw = data.get("raw_review") or ""
    new = {
        "wingman_schema_version": "4",
        "branch": data.get("branch"),
        "timestamp": data.get("timestamp"),
        "base": data.get("base", "main"),
        "reviewer": _build_reviewer(raw),
        "raw_review": raw,
        "parsed_findings": data.get("parsed_findings", []),
        "findings": data.get("findings", []),
        "resolutions": data.get("resolutions", []),
        "status": data.get("status", "needs_categorization"),
    }
    path.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
    return True


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    review_dir = Path(args[0] if args else ".reviews")
    if not review_dir.is_dir():
        print(f"error: {review_dir} is not a directory", file=sys.stderr)
        return 1

    hook = _find_hook(review_dir)
    parser_ns = _load_parser(hook) if hook else None
    if parser_ns is None:
        print(
            "  note: no v5+ hook found for this repo — migrating shape only, no backfill.\n"
            "        Install the current hook (/review-setup) and re-run to recover findings.",
            file=sys.stderr,
        )
    elif dry_run:
        print("  dry-run: no files will be written")

    migrated = 0
    skipped = 0
    failed = 0
    for path in sorted(review_dir.glob("*.json")):
        # NOT every .json in .reviews/ is a review artifact. `_convergence.json`
        # is the round-tracking ledger ({branch, rounds[], convergence{}}) and
        # any future underscore-prefixed file is likewise internal state.
        # Reshaping one destroys it — caught after doing exactly that to a live
        # ledger, 2026-08-15. Skip by name AND by shape: an artifact always
        # carries `raw_review`.
        if path.name.startswith("_"):
            skipped += 1
            continue
        try:
            probe = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failed += 1
            print(f"  failed:   {path} — {exc}", file=sys.stderr)
            continue
        if not isinstance(probe, dict) or "raw_review" not in probe:
            skipped += 1
            continue
        try:
            if migrate(path, parser_ns=parser_ns, dry_run=dry_run):
                migrated += 1
                print(f"  migrated: {path}")
            else:
                skipped += 1
        except (OSError, json.JSONDecodeError) as exc:
            failed += 1
            print(f"  failed:   {path} — {exc}", file=sys.stderr)

    verb = "would migrate" if dry_run else "migrated"
    print(f"wingman migrate-reviews: {migrated} {verb}, {skipped} unchanged, {failed} failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
