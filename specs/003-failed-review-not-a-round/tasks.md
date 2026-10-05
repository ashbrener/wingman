# Tasks: A review that did not run is not a round

**Input**: plan.md (D1–D6), research.md (R-1 … R-7), data-model.md,
contracts/review-outcome.md, quickstart.md, spec.md (US1–US3, FR-001..011,
SC-001..005)

**Test strategy (R-7)**: `scripts/verify-convergence.py` extracts the payload
writer from the hook and drives it across push sequences. It is written FIRST
and must fail against the v5 hook for the right reason (missing runs counted as
rounds, stop-rule met).

**MVP**: Phase 3 (US1+US2 share one code block — classifying without excluding,
or excluding without classifying, is half a fix).

---

## Phase 1: Setup

- [X] T001 Add `tests/fixtures/codex-401.txt`: a codex run that failed
  authentication — banner, prompt echo, then `ERROR: unexpected status 401
  Unauthorized` as the final lines.
- [X] T002 Add `tests/fixtures/reviewer-missing.txt`: the exact two lines the hook
  writes when the reviewer is not on PATH.

## Phase 2: Foundational (blocking)

- [X] T003 Write `scripts/verify-convergence.py`: assert the `WINGMAN_PYEOF`
  heredoc delimiters appear exactly once in `assets/pre-push.sample`, extract the
  payload writer, and run it per push with the hook's env vars in a scratch
  directory. Sequences per quickstart.md. It must FAIL against the v5 hook
  (two missing runs meet the stop-rule) — that failure is the red test.

**Checkpoint**: the verifier fails on `missing → missing` with the stop-rule met.

## Phase 3: US1 + US2 — failed runs are not rounds (P1) 🎯 MVP

- [X] T004 [US1] In `assets/pre-push.sample`, capture the reviewer's exit status
  in `_reviewer_exit` on every path (codex with and without `WINGMAN_MODEL`, the
  `--prompt-file` retry recording the last attempt; gemini; claude), leaving it
  empty for missing/unknown reviewers, and pass it as `WINGMAN_REVIEWER_EXIT`.
- [X] T005 [US1] In the payload writer, add `_REVIEW_FAILURE_SIGNATURES` and
  `_classify_review(raw, tool, exit_status)` implementing research R-3, with a
  comment stating the rule and its bias.
- [X] T006 [US2] Branch the ledger update: succeeded → existing round logic,
  unchanged; failed/missing → append to `uncounted_runs`, leave `rounds` and the
  ledger `convergence` summary untouched, report `round: null`,
  `stop_rule_met: false`, trend `n/a`, no stagnation, streak unchanged.
- [X] T007 [US1] Emit `review_outcome` and `convergence.counted`; set status
  `review_failed` / `reviewer_missing`; add a `[REVIEW FAILED]` /
  `[REVIEWER MISSING]` notice; keep `raw_review`.
- [X] T008 Bump the marker `# wingman-hook-version: 5` → `6`; add the v6 History
  entry naming the defect.
- [X] T009 Run `python3 scripts/verify-convergence.py` and
  `python3 scripts/verify-parser.py` — both green (SC-001 … SC-005).

## Phase 4: US3 + durability

- [X] T010 [P] `.github/workflows/wingman-ci.yml`: run the new verifier; smoke
  assertions expect marker 6; scenario 7 also asserts the missing run is not a
  round.
- [X] T011 [P] `README.md`: current version 6 everywhere; "What's new in v6" and
  the missing v5 entry; document the failure rule and `review_outcome`.
- [X] T012 [P] `skills/review-loop/SKILL.md`: current version 6, drift threshold
  6; `review_failed` / `reviewer_missing` artifacts are not reviews — say so,
  never treat them as clean.

## Phase 4b: US4 — failing CI is never read as "no CI" (P1)

- [X] T015 [US4] Extend `scripts/verify-convergence.py`: slice the CI block
  from the hook between its unique headers, run it with a fake `gh` that
  prints failing-check JSON and exits 1 (plus pending/exit 8, green/exit 0,
  no output/exit 1, garbage/exit 1), and feed the result through two clean
  reviews. It must FAIL against the `|| fallback` block (CI recorded as NONE,
  no synthetic P1, stop-rule met) — that failure is the red test.
- [X] T016 [US4] In `assets/pre-push.sample`, capture `gh pr checks` output in
  `_ci_raw` and its exit status in `_ci_rc`; write the output whenever it is
  non-empty valid JSON; otherwise write `UNKNOWN` with `gh_exit`.
- [X] T017 Add the CI fix to the v6 History entry (marker stays 6) and to the
  README's "What's new in v6".

## Phase 5: Verification

- [X] T013 `bash -n` and `shellcheck --severity=error` on the hook; `py_compile`
  the extracted payload writer.
- [X] T014 Replay the CI install-smoke scenarios locally against the patched hook.

## Dependencies

- T001/T002 → T003 (red) → T004–T008 → T009 (green) → Phase 4 → Phase 5.
- T010/T011/T012 touch disjoint files.
