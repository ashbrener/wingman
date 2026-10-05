# Implementation Plan: A review that did not run is not a round

**Branch**: `fix/failed-review-not-a-round` | **Date**: 2026-10-05 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-failed-review-not-a-round/spec.md`

## Summary

Record each review's outcome explicitly — `succeeded`, `failed` or `missing` —
and let only succeeded reviews become convergence rounds. The hook captures the
reviewer's exit status instead of discarding it with `|| true`; the payload
writer classifies the run with one documented per-reviewer rule; failed and
missing runs are written as artifacts (marked, raw output kept) and logged in
the ledger as `uncounted_runs`, outside `rounds`, so the stop-rule, streak,
stagnation and trend arithmetic never sees them. Decisions in
[research.md](research.md) (R-1 … R-7).

## Technical Context

**Language/Version**: Bash + inline Python 3 (stdlib only), as today

**Primary Dependencies**: none added

**Storage**: the review artifact JSON under `.reviews/` and `_convergence.json`
— both extended additively; artifact schema stays 4

**Testing**: NEW `scripts/verify-convergence.py` extracts the payload writer from
the hook and drives it across push sequences with recorded fixtures (R-7);
`scripts/verify-parser.py` unchanged; both in CI

**Target Platform**: any repo installing the hook (macOS/Linux)

**Project Type**: git-hook + skills pack (single artifact: `assets/pre-push.sample`)

**Constraints**: no new dependency · hook never blocks a push · successful
reviews behave exactly as in v5 · older ledgers remain valid

## Constitution Check

`.specify/memory/constitution.md` is still an unratified template (see spec 002's
plan), so there is no project gate to evaluate. Against the pack's own published
discipline:

- **Review is advisory, never blocking** — unchanged. PASS.
- **A signal must be able to fail** — this is the point of the change: "no
  review ran" can no longer read as "clean". PASS.
- **Single source of truth** — the classifier lives once, in the hook; the
  verifier extracts and runs it. PASS.

## Project Structure

```text
specs/003-failed-review-not-a-round/
├── spec.md · plan.md · research.md · data-model.md · quickstart.md · tasks.md
├── contracts/review-outcome.md
└── checklists/requirements.md

assets/pre-push.sample            # the ONLY behavioural change:
                                  #   + capture reviewer exit status
                                  #   + _classify_review() + signatures
                                  #   + uncounted runs kept out of rounds
                                  #   + review_outcome, status review_failed
                                  #   + marker → wingman-hook-version: 6
scripts/verify-convergence.py     # NEW — drives the payload writer
tests/fixtures/
├── codex-401.txt                 # a codex run that failed authentication
└── reviewer-missing.txt          # the hook's missing-reviewer sentinel
.github/workflows/wingman-ci.yml  # + verifier step, marker 6 in smoke tests
README.md                         # current version 6, What's new v6 (+ v5)
skills/review-loop/SKILL.md       # version 6; review_failed is not a clean round
```

## Design decisions (binding for /speckit-tasks)

- **D1** (R-2): capture `WINGMAN_REVIEWER_EXIT`; classify in Python via
  `_classify_review(raw, tool, exit_status)`.
- **D2** (R-3): the five-step rule; signatures per reviewer, tail-only,
  line-anchored, and only on findings-free output.
- **D3** (R-4): `rounds` holds succeeded reviews only; failed/missing go to
  `uncounted_runs`; the ledger `convergence` summary is not recomputed on an
  uncounted run.
- **D4** (R-5): artifact gets `review_outcome`, `convergence.counted`,
  `round: null`, `stop_rule_met: false`, status `review_failed` /
  `reviewer_missing`, and an explanatory notice.
- **D5** (R-6): hook marker 5 → 6; schema stays 4.
- **D6** (R-7): `scripts/verify-convergence.py` + fixtures, wired into CI.
