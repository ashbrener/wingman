#!/usr/bin/env python3
"""Verify round counting in the payload writer inside ``assets/pre-push.sample``.

Spec 003: a review that did not run — reviewer CLI missing, or a reviewer that
exited with an error such as a codex 401 — must never count as a convergence
round. Before the fix, two such pushes met the stop-rule and printed a
convergence notice on a branch nobody had reviewed.

Convergence is ledger arithmetic across several pushes, so this verifier runs
the hook's payload writer end to end, exactly as the hook does (same env vars,
a scratch ``.reviews/``), across push sequences built from recorded fixtures.
The writer is SINGLE-SOURCED in the hook: it is extracted between its heredoc
delimiters, each asserted to appear exactly once, never copied.

It also runs the hook's CI-awareness block in bash against a fake ``gh``:
``gh pr checks`` prints valid JSON but EXITS 1 when any check fails (8 when
any is pending), and the hook used to replace that JSON with an empty list on
the non-zero exit — recording CI as NONE, dropping the synthetic red-CI P1,
and letting a branch with failing CI converge.

Run: ``python3 scripts/verify-convergence.py``  ·  exit 0 = green, 1 = mismatch.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
HOOK = REPO / "assets" / "pre-push.sample"
FIXTURES = REPO / "tests" / "fixtures"

OPEN = "python3 - <<'WINGMAN_PYEOF'"
CLOSE = "\nWINGMAN_PYEOF\n"

CI_OPEN = "        # --- v3 Feature 2: CI awareness"
CI_CLOSE = "        # --- Reviewer metadata extraction"

CLEAN = (FIXTURES / "no-findings.txt").read_text()
FINDINGS = (FIXTURES / "incident-native.txt").read_text()
CODEX_401 = (FIXTURES / "codex-401.txt").read_text()
MISSING = (FIXTURES / "reviewer-missing.txt").read_text()


def load_writer() -> str:
    """The payload writer's Python source, sliced from the hook."""
    text = HOOK.read_text()
    for delim in (OPEN, CLOSE):
        count = text.count(delim)
        if count != 1:
            raise SystemExit(
                f"FAIL: {delim.strip()!r} appears {count} times in {HOOK} — expected exactly 1."
            )
    return text.split(OPEN, 1)[1].split(CLOSE, 1)[0].lstrip("\n")


def load_ci_block() -> str:
    """The hook's CI-awareness bash block, sliced between its unique headers."""
    text = HOOK.read_text()
    for delim in (CI_OPEN, CI_CLOSE):
        count = text.count(delim)
        if count != 1:
            raise SystemExit(f"FAIL: {delim.strip()!r} appears {count} times in {HOOK} — expected exactly 1.")
    return CI_OPEN + text.split(CI_OPEN, 1)[1].split(CI_CLOSE, 1)[0]


FAKE_GH = """#!/bin/bash
# A stand-in for gh: `pr list` names PR 20; `pr checks` prints $FAKE_GH_CHECKS
# (if set) and exits $FAKE_GH_EXIT — real gh exits 1 on failing checks, 8 on
# pending, while still printing the JSON.
case "$1 $2" in
    "pr list") echo 20 ;;
    "pr checks") [ -n "${FAKE_GH_CHECKS:-}" ] && printf '%s\\n' "$FAKE_GH_CHECKS"; exit "${FAKE_GH_EXIT:-0}" ;;
esac
"""


def run_ci_block(checks: str | None, gh_exit: int) -> str:
    """Run the hook's CI block with a fake gh; return what it wrote for the writer."""
    d = pathlib.Path(tempfile.mkdtemp(prefix="wingman-ci-"))
    (d / "bin").mkdir()
    gh = d / "bin" / "gh"
    gh.write_text(FAKE_GH)
    gh.chmod(0o755)
    script = d / "ci.sh"
    script.write_text(
        '_ci_status_file="$1"; _ci_summary_file="$2"; WINGMAN_BRANCH=feat/x\n'
        + load_ci_block()
    )
    env = dict(os.environ)
    env["PATH"] = f"{d / 'bin'}:{env.get('PATH', '')}"
    env["FAKE_GH_EXIT"] = str(gh_exit)
    if checks is not None:
        env["FAKE_GH_CHECKS"] = checks
    proc = subprocess.run(
        ["bash", str(script), str(d / "ci.json"), str(d / "cisum.txt")],
        env=env, capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"FAIL: CI block crashed:\n{proc.stderr}")
    return (d / "ci.json").read_text()


class Repo:
    """A scratch working directory standing in for one branch's pushes."""

    def __init__(self, writer: str):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="wingman-conv-"))
        (self.dir / ".reviews").mkdir()
        self.writer = self.dir / "payload.py"
        self.writer.write_text(writer)
        (self.dir / "ci.json").write_text("[]")
        self.n = 0

    def push(self, raw: str, tool: str = "codex", exit_status: int | None = 0,
             ci: str = "[]") -> dict:
        """Run the writer once, as one push; return the artifact it wrote."""
        self.n += 1
        (self.dir / "ci.json").write_text(ci)
        review_in = self.dir / f"review-{self.n}.txt"
        review_in.write_text(raw)
        artifact = self.dir / ".reviews" / f"2026-10-05-00000{self.n}-feat-x.json"
        env = dict(os.environ)
        env.update({
            "WINGMAN_REVIEW_INPUT": str(review_in),
            "WINGMAN_TOOL": tool,
            "WINGMAN_REVIEWER_EXIT": "" if exit_status is None else str(exit_status),
            "WINGMAN_CI_STATUS_INPUT": str(self.dir / "ci.json"),
            "WINGMAN_PR_NUMBER": "",
            "WINGMAN_TOOL_VERSION": "test",
            "WINGMAN_MODEL_USED": "test-model",
            "WINGMAN_PROVIDER": "test",
            "WINGMAN_REASONING": "",
            "WINGMAN_SESSION_ID": "",
            "WINGMAN_WALL_SECONDS": "1",
            "WINGMAN_BRANCH": "feat/x",
            "WINGMAN_TIMESTAMP": f"2026-10-05-00000{self.n}",
            "WINGMAN_BASE": "main",
            "WINGMAN_REVIEW_FILE": str(artifact),
            "WINGMAN_EXEMPTIONS_FILE": "",
            "WINGMAN_CONVERGENCE_FILE": str(self.dir / ".reviews" / "_convergence.json"),
        })
        if exit_status is None:
            del env["WINGMAN_REVIEWER_EXIT"]  # an older caller that never passed it
        proc = subprocess.run(
            [sys.executable, str(self.writer)], cwd=self.dir, env=env,
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(f"FAIL: payload writer crashed:\n{proc.stderr}")
        return json.loads(artifact.read_text())

    @property
    def ledger(self) -> dict:
        return json.loads((self.dir / ".reviews" / "_convergence.json").read_text())


def check(label: str, cond: bool, detail: object = "") -> bool:
    print(f"  {'PASS' if cond else 'FAIL'}  {label}{'' if cond else f' — {detail}'}")
    return cond


def converged(art: dict) -> bool:
    return any(n.startswith("[CONVERGENCE NOTICE]") for n in art.get("notices", []))


def outcome(art: dict) -> str | None:
    return (art.get("review_outcome") or {}).get("state")


def main() -> int:
    writer = load_writer()
    ok = True

    # SC-001 — the reported defect: two missing-reviewer pushes met the stop-rule.
    print("missing -> missing (SC-001)")
    r = Repo(writer)
    a1 = r.push(MISSING, exit_status=None)
    a2 = r.push(MISSING, exit_status=None)
    ok &= check("stop-rule not met", not a2["convergence"]["stop_rule_met"], a2["convergence"])
    ok &= check("no convergence notice", not converged(a1) and not converged(a2), a2["notices"])
    ok &= check("no rounds recorded", len(r.ledger["rounds"]) == 0, r.ledger["rounds"])
    ok &= check("both runs logged as uncounted", len(r.ledger.get("uncounted_runs", [])) == 2,
                r.ledger.get("uncounted_runs"))
    ok &= check("ledger never claims a stop-rule round",
                not r.ledger["convergence"].get("stop_rule_met_at_round"), r.ledger["convergence"])
    ok &= check("artifacts marked missing", [a1["status"], a2["status"]] == ["reviewer_missing"] * 2
                and outcome(a2) == "missing", [a1["status"], a2["status"], outcome(a2)])
    ok &= check("round is null and uncounted",
                a2["convergence"]["round"] is None and a2["convergence"].get("counted") is False,
                a2["convergence"])

    # SC-002 — the live incident: codex not logged in, HTTP 401, non-zero exit.
    print("codex 401 -> codex 401 (SC-002)")
    r = Repo(writer)
    a1 = r.push(CODEX_401, exit_status=1)
    a2 = r.push(CODEX_401, exit_status=1)
    ok &= check("stop-rule not met", not a2["convergence"]["stop_rule_met"], a2["convergence"])
    ok &= check("no convergence notice", not converged(a1) and not converged(a2), a2["notices"])
    ok &= check("no rounds recorded", len(r.ledger["rounds"]) == 0, r.ledger["rounds"])
    ok &= check("artifacts marked failed", a2["status"] == "review_failed" and outcome(a2) == "failed",
                [a2["status"], a2.get("review_outcome")])
    ok &= check("exit status recorded", (a2.get("review_outcome") or {}).get("exit_status") == 1, a2.get("review_outcome"))
    ok &= check("raw output kept for the author", "401 Unauthorized" in a2["raw_review"])
    ok &= check("failure notice explains it was not counted",
                any(n.startswith("[REVIEW FAILED]") for n in a2["notices"]), a2["notices"])

    print("codex 401 with exit 0 (signature at the tail)")
    r = Repo(writer)
    a = r.push(CODEX_401, exit_status=0)
    ok &= check("classified failed", outcome(a) == "failed", a.get("review_outcome"))
    ok &= check("not a round", len(r.ledger["rounds"]) == 0, r.ledger["rounds"])

    # SC-003 — an outage between two clean rounds neither breaks nor advances the streak.
    print("clean -> codex 401 -> clean (SC-003)")
    r = Repo(writer)
    a1 = r.push(CLEAN)
    summary_after_round_1 = r.ledger["convergence"]
    a2 = r.push(CODEX_401, exit_status=1)
    ok &= check("failed run is not a round", a2["convergence"]["round"] is None, a2["convergence"])
    ok &= check("failed run does not meet the stop-rule", not a2["convergence"]["stop_rule_met"])
    ok &= check("streak unchanged by the failure",
                a2["convergence"]["consecutive_zero_p1_rounds"] == 1, a2["convergence"])
    ok &= check("ledger summary untouched by the failure",
                r.ledger["convergence"] == summary_after_round_1, r.ledger["convergence"])
    a3 = r.push(CLEAN)
    ok &= check("second clean run is round 2", a3["convergence"]["round"] == 2, a3["convergence"])
    ok &= check("stop-rule met on round 2", a3["convergence"]["stop_rule_met"], a3["convergence"])
    ok &= check("streak is 2", a3["convergence"]["consecutive_zero_p1_rounds"] == 2, a3["convergence"])
    ok &= check("ledger: 2 rounds, 1 uncounted",
                len(r.ledger["rounds"]) == 2 and len(r.ledger["uncounted_runs"]) == 1,
                (len(r.ledger["rounds"]), len(r.ledger.get("uncounted_runs", []))))

    print("findings -> failed -> clean (trend/streak compare real rounds)")
    r = Repo(writer)
    r.push(FINDINGS)
    r.push("", exit_status=0)  # empty output: no evidence of a review
    a3 = r.push(CLEAN)
    ok &= check("clean run is round 2", a3["convergence"]["round"] == 2, a3["convergence"])
    ok &= check("stop-rule not met (round 1 had P1)", not a3["convergence"]["stop_rule_met"])
    ok &= check("trend compares against round 1", a3["convergence"]["trend"] == "converging",
                a3["convergence"]["trend"])
    ok &= check("streak is 1", a3["convergence"]["consecutive_zero_p1_rounds"] == 1, a3["convergence"])

    # SC-004 — real reviews behave exactly as before.
    print("clean -> clean (SC-004)")
    r = Repo(writer)
    a1 = r.push(CLEAN)
    a2 = r.push(CLEAN)
    ok &= check("both succeeded", outcome(a1) == outcome(a2) == "succeeded", [outcome(a1), outcome(a2)])
    ok &= check("stop-rule met on round 2",
                a2["convergence"]["round"] == 2 and a2["convergence"]["stop_rule_met"], a2["convergence"])
    ok &= check("convergence notice emitted", converged(a2), a2["notices"])

    print("findings -> findings")
    r = Repo(writer)
    r.push(FINDINGS)
    a2 = r.push(FINDINGS)
    ok &= check("stop-rule not met", not a2["convergence"]["stop_rule_met"], a2["convergence"])
    ok &= check("counts non-zero", a2["convergence"]["p1_count"] == 2, a2["convergence"])

    # FR-008 — an error signature never discards a review that reported findings.
    print("findings ending in an error-like line, exit 0 (FR-008)")
    r = Repo(writer)
    a = r.push(FINDINGS + "ERROR: unexpected status 401 Unauthorized\n")
    ok &= check("classified succeeded", outcome(a) == "succeeded", a.get("review_outcome"))
    ok &= check("counted as round 1", a["convergence"]["round"] == 1, a["convergence"])

    print("clean review that quoted a 401 mid-transcript, exit 0")
    r = Repo(writer)
    quoted = CODEX_401 + "".join(f"codex note {i}: the change is fine.\n" for i in range(6)) + CLEAN
    a = r.push(quoted)
    ok &= check("classified succeeded (only the tail is inspected)", outcome(a) == "succeeded",
                a.get("review_outcome"))

    print("non-zero exit with output (claude)")
    r = Repo(writer)
    a = r.push("Invalid API key · Please run /login\n", tool="claude", exit_status=1)
    ok &= check("classified failed", outcome(a) == "failed", a.get("review_outcome"))
    a = r.push("Invalid API key · Please run /login\n", tool="claude", exit_status=0)
    ok &= check("signature alone (exit 0) also failed", outcome(a) == "failed", a.get("review_outcome"))

    print("gemini auth error, exit 0")
    r = Repo(writer)
    a = r.push("Please set an Auth method in your settings.json or specify GEMINI_API_KEY\n",
               tool="gemini", exit_status=0)
    ok &= check("classified failed", outcome(a) == "failed", a.get("review_outcome"))

    # gh pr checks exits 1 on failing checks while printing valid JSON. That
    # JSON must reach the writer: CI red is a synthetic P1, so a branch with
    # failing CI can never converge.
    failing = json.dumps([
        {"name": "quality-gate", "state": "FAILURE", "link": "https://ci.example/1"},
        {"name": "lint", "state": "SUCCESS", "link": "https://ci.example/2"},
    ])
    print("gh pr checks: failing checks, exit 1")
    ci = run_ci_block(failing, 1)
    r = Repo(writer)
    r.push(CLEAN, ci=ci)
    a = r.push(CLEAN, ci=ci)
    ok &= check("CI recorded as FAILURE", a["ci_status"]["state"] == "FAILURE", a["ci_status"])
    ok &= check("failing check named", [f["name"] for f in a["ci_status"]["failing"]] == ["quality-gate"],
                a["ci_status"]["failing"])
    ok &= check("synthetic red-CI P1 present",
                any(f.startswith("[P1] CI status: quality-gate") for f in a["synthetic_findings"]),
                a["synthetic_findings"])
    ok &= check("p1_count includes the red CI", a["convergence"]["p1_count"] == 1, a["convergence"])
    ok &= check("stop-rule not met", not a["convergence"]["stop_rule_met"], a["convergence"])
    ok &= check("no convergence notice", not converged(a), a["notices"])

    print("gh pr checks: pending checks, exit 8")
    ci = run_ci_block(json.dumps([{"name": "tests", "state": "PENDING", "link": ""}]), 8)
    a = Repo(writer).push(CLEAN, ci=ci)
    ok &= check("CI recorded as PENDING", a["ci_status"]["state"] == "PENDING", a["ci_status"])

    print("gh pr checks: all green, exit 0")
    ci = run_ci_block(json.dumps([{"name": "tests", "state": "SUCCESS", "link": ""}]), 0)
    a = Repo(writer).push(CLEAN, ci=ci)
    ok &= check("CI recorded as SUCCESS", a["ci_status"]["state"] == "SUCCESS", a["ci_status"])
    ok &= check("no synthetic finding", a["synthetic_findings"] == [], a["synthetic_findings"])

    print("gh pr checks: no usable output (error, or unparseable)")
    for label, out, rc in (("no output, exit 1", None, 1), ("garbage, exit 1", "HTTP 502 Bad Gateway", 1)):
        ci = run_ci_block(out, rc)
        try:
            parsed = json.loads(ci)
        except json.JSONDecodeError:
            parsed = None
        ok &= check(f"{label}: falls back to UNKNOWN",
                    isinstance(parsed, dict) and parsed.get("state") == "UNKNOWN", ci)

    print("exit status not passed (older caller)")
    r = Repo(writer)
    a = r.push(CLEAN, exit_status=None)
    ok &= check("clean output still succeeds", outcome(a) == "succeeded", a.get("review_outcome"))
    ok &= check("exit status recorded as null", (a.get("review_outcome") or {}).get("exit_status", "absent") is None,
                a.get("review_outcome"))

    print("\nverify-convergence:", "OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
