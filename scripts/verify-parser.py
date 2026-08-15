#!/usr/bin/env python3
"""Verify the review-finding parser that lives inside ``assets/pre-push.sample``.

The parser is SINGLE-SOURCED in the hook — there is no importable copy, because
two copies of a load-bearing regex is exactly the divergence that caused the
defect this feature fixes (spec 002). So this verifier extracts the parser
block from the hook between two unique anchor comments, executes just that
block, and exercises it against recorded fixtures.

Anchors are asserted UNIQUE before slicing: an anchor that appears twice (for
example quoted in a comment that describes it) would silently slice the wrong
region and "pass" against nothing.

Run: ``python3 scripts/verify-parser.py``  ·  exit 0 = green, 1 = mismatch.
"""

from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / "assets" / "pre-push.sample"
FIXTURES = REPO / "tests" / "fixtures"

BEGIN = "# --- BEGIN finding parser (verified by scripts/verify-parser.py) ---"
END = "# --- END finding parser ---"


def load_parser() -> dict:
    """Exec the anchored parser block from the hook; return its namespace."""
    text = HOOK.read_text()
    for anchor in (BEGIN, END):
        count = text.count(anchor)
        if count != 1:
            raise SystemExit(
                f"FAIL: anchor {anchor!r} appears {count} times in {HOOK} — expected exactly 1.\n"
                "The parser block must be fenced by exactly one BEGIN and one END."
            )
    block = text.split(BEGIN, 1)[1].split(END, 1)[0]
    namespace: dict = {"re": re}
    exec(block, namespace)  # noqa: S102 — executing our own fenced source, by design
    for name in ("_parse_findings", "_count_pri"):
        if name not in namespace:
            raise SystemExit(f"FAIL: parser block does not define {name}()")
    return namespace


def counts(ns: dict, text: str) -> tuple[int, int, int]:
    """The hook's own counting rule: MAX of the native parse and the legacy grep."""
    parsed = ns["_parse_findings"](text)
    out = []
    for tag in ("P1", "P2", "P3"):
        native = len([f for f in parsed if f["priority"] == tag])
        out.append(max(native, ns["_count_pri"](text, tag)))
    return tuple(out)  # type: ignore[return-value]


def check(label: str, cond: bool, detail: str = "") -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'' if cond else f' — {detail}'}")
    return cond


def main() -> int:
    ns = load_parser()
    ok = True

    # SC-001 — the recorded incident: 3 findings (2 high → P1, 1 medium → P2)
    # where the pre-fix hook reported 0 and declared convergence.
    raw = (FIXTURES / "incident-native.txt").read_text()
    parsed = ns["_parse_findings"](raw)
    print("incident-native.txt (the recorded live incident)")
    ok &= check("3 findings parsed", len(parsed) == 3, f"got {len(parsed)}")
    if len(parsed) == 3:
        ok &= check(
            "priorities are P1,P1,P2",
            [f["priority"] for f in parsed] == ["P1", "P1", "P2"],
            str([f["priority"] for f in parsed]),
        )
        ok &= check(
            "files and lines captured",
            all(f["file"].endswith(".py") and isinstance(f["line"], int) for f in parsed),
            str([(f["file"], f["line"]) for f in parsed]),
        )
        ok &= check(
            "categories from the closed vocabulary",
            all(f["category"] in {"lint", "logic", "architecture", "security"} for f in parsed),
            str([f["category"] for f in parsed]),
        )
    p1, p2, _p3 = counts(ns, raw)
    ok &= check("counts non-zero (stop-rule cannot fire)", p1 == 2 and p2 == 1, f"p1={p1} p2={p2}")

    # SC-004 — the legacy [P1] shape must still count; supporting one shape
    # never removes the other.
    raw = (FIXTURES / "legacy-priority.txt").read_text()
    print("legacy-priority.txt (gemini/claude contract)")
    p1, p2, _p3 = counts(ns, raw)
    ok &= check("legacy shape still counted", p1 >= 1 and p2 >= 1, f"p1={p1} p2={p2}")

    # SC-003 — a genuinely clean review still reports clean, so the fix cannot
    # be achieved by counting everything.
    raw = (FIXTURES / "no-findings.txt").read_text()
    print("no-findings.txt (honest zero)")
    ok &= check("no findings parsed", ns["_parse_findings"](raw) == [])
    ok &= check("counts are zero", counts(ns, raw) == (0, 0, 0), str(counts(ns, raw)))

    # SC-005 — prose containing pipes and paths is not a finding; the closed
    # category+severity vocabulary is the qualifying test.
    raw = (FIXTURES / "prose-with-pipes.txt").read_text()
    print("prose-with-pipes.txt (false-positive guard)")
    found = ns["_parse_findings"](raw)
    ok &= check("no false positives", found == [], str(found))
    ok &= check("counts are zero", counts(ns, raw) == (0, 0, 0), str(counts(ns, raw)))

    # Regression (found by the first real end-to-end run): a reviewer quoting
    # a DIFF must not manufacture findings — "+path | logic | high | ..." is a
    # diff-added line, not a report. Diff markers are not filenames.
    raw = (FIXTURES / "diff-quoted.txt").read_text()
    print("diff-quoted.txt (diff markers are not filenames)")
    found = ns["_parse_findings"](raw)
    ok &= check("no findings from quoted diff lines", found == [], str([f["file"] for f in found]))

    print("\nverify-parser:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
