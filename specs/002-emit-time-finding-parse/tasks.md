# Tasks: Findings parsed at emit time

**Input**: plan.md (D1–D8), research.md (R-1 … R-7), data-model.md,
contracts/review-artifact-v4.md, quickstart.md, spec.md (US1–US3, FR-001..012,
SC-001..007)

**Test strategy (R-7)**: this repo has no python suite and does not gain one.
`scripts/verify-parser.py` extracts the parser from the hook between unique
anchors and runs it against four recorded fixtures. The verifier and fixtures
are written FIRST and must fail against the current parser-less hook.

**MVP**: Phase 3 (US1+US2 together — they share one code block; a parsed array
nobody counts, or counts with nothing parsed, is half a fix).

---

## Phase 1: Setup

- [X] T001 Capture the incident evidence verbatim before touching code: copy the recorded codex review body from the live artifact (`~/Code/PP/backend/.reviews/2026-08-15-215127-*.json`, field `raw_review`) into `tests/fixtures/incident-native.txt` — three findings, two `high`, one `medium`. Do not reformat it; it is the acceptance oracle for SC-001.

## Phase 2: Foundational (blocking)

- [X] T002 Add the remaining three fixtures: `tests/fixtures/legacy-priority.txt` (a `[P1]`/`[P2]` shaped review), `tests/fixtures/no-findings.txt` (exactly `NO FINDINGS`), `tests/fixtures/prose-with-pipes.txt` (a `## Notes` section whose prose contains `|` characters and file paths but no valid category/severity pair).
- [X] T003 Write `scripts/verify-parser.py`: locate `assets/pre-push.sample`, assert each anchor comment appears EXACTLY once, slice the parser block between them, `exec` it in an isolated namespace with `re` available, then assert per fixture — incident: 3 parsed, priorities `[P1,P1,P2]`; legacy: 0 parsed but legacy grep ≥1 so `max()` is non-zero; no-findings: 0 parsed, 0 counted; prose: 0 parsed. Exit non-zero with a readable diff on any mismatch. It must FAIL right now (no anchors exist yet) — that failure is the red test.

**Checkpoint**: `python3 scripts/verify-parser.py` fails for the right reason (anchors absent), proving the harness tests the hook rather than a copy.

## Phase 3: US1 + US2 — the artifact tells the truth (P1) 🎯 MVP

**Goal**: parsed findings are emitted (US1) and every count derives from them (US2).
**Independent test**: quickstart's replay — the incident fixture yields 3 findings, p1=2, p2=1, `stop_rule_met` false, no convergence notice.

- [X] T004 [US1] In `assets/pre-push.sample`, add the anchored parser block immediately above the existing `_count_pri` definition, fenced by two unique comments (e.g. `# --- BEGIN finding parser (verified by scripts/verify-parser.py) ---` / `# --- END finding parser ---`): the severity→priority map (`critical|high→P1`, `medium→P2`, `low→P3`), the line regex per contracts/review-artifact-v4.md (optional `:line`; description may contain pipes), and `_parse_findings(text)` returning file/line/category/severity/priority/description. The closed category AND severity vocabularies are the qualifying test (D4) — a shape-only match must not qualify.
- [X] T005 [US2] In `assets/pre-push.sample`, keep `_count_pri` exactly as-is and change only the count assignments to `max(len([f for f in parsed_findings if f["priority"] == "P{n}"]), _count_pri(raw, "P{n}"))` for P1/P2/P3 (D2). The synthetic CI-red contribution to `p1_count` must remain, applied after the max.
- [X] T006 [US2] In `assets/pre-push.sample`, append `file:line` (or bare `file` when the line is absent) identities from `parsed_findings` to the existing `finding_ids` heuristics — appended, never replacing the `[P1] <id>` / `Finding <id>` extraction (D5).
- [X] T007 [US1] In `assets/pre-push.sample`, emit `"parsed_findings": parsed_findings` in the document immediately above `"findings": []`, with a comment stating that `findings` remains the review loop's categorization target and that readers asking "what did the reviewer find" read `parsed_findings` (D1). Bump `"wingman_schema_version"` to `"4"`.
- [X] T008 [US1] In `assets/pre-push.sample`, bump the marker `# wingman-hook-version: 4` → `5`, update the header's schema-shape line to v4, and add the History entry naming the defect (codex's native shape vs the legacy-only counter; stop-rule fired on round one while findings sat unread; found live across four arcs 2026-08-15).
- [X] T009 Run `python3 scripts/verify-parser.py` — all four fixtures pass. This is SC-001 + SC-003 + SC-005 together.

**Checkpoint**: the incident replays green; a clean review still converges.

## Phase 4: US3 — migration, CI, and the docs that describe the shape (P2)

- [X] T010 [US3] Extend `scripts/migrate-reviews.py` with the 3→4 step: add `parsed_findings: []` when absent, set `wingman_schema_version: "4"`, leave every other field untouched; older artifacts must remain readable and an empty array must be documented as "written before parsing existed" (FR-010, SC-007).
- [X] T011 [P] Add a verifier step to `.github/workflows/wingman-ci.yml` running `python3 scripts/verify-parser.py`, so the parser can never regress silently.
- [X] T012 [P] Update `skills/review-loop/SKILL.md`: document `parsed_findings` in the artifact shape, state that it is machine-parsed at emit time and never categorized, and instruct the loop to read it (falling back to `raw_review` for older artifacts) rather than concluding "clean" from an empty `findings`.
- [X] T013 [P] Update `skills/review-setup/SKILL.md`: the current hook version is **5**; note that re-running setup replaces the marked block in place.

## Phase 5: Polish & verification

- [X] T014 Re-read the full patched heredoc in `assets/pre-push.sample` for shell-quoting safety: the block lives inside a quoted heredoc, so `$`, backticks and backslashes in the regex must survive expansion exactly as written (verify by running the verifier, which reads the file as text, AND by a real hook run in T015).
- [X] T015 End-to-end on this branch: install the patched hook locally (`/review-setup` or a manual copy into `.git/hooks/pre-push`), push, and confirm — the push is NOT blocked, `.reviews/<stamp>-fix-emit-time-finding-parse.json` exists with `wingman_schema_version: "4"`, `parsed_findings` populated if the reviewer found anything, `findings: []`, and counts matching what the raw output actually says (SC-002, SC-006).
- [X] T016 Confirm an artifact written by the previous version still loads through `scripts/migrate-reviews.py` and reads correctly (SC-007), using one of tonight's live v3/v2 files as the input.

## Phase 6: Backfill the recorded backlog (FR-010a, SC-008)

- [X] T017 Extend `scripts/migrate-reviews.py` to BACKFILL: locate the installed hook (honouring `core.hooksPath`, else `.git/hooks/pre-push`) for the repo owning the `.reviews/` directory, extract the anchored parser from it (the same single-source extraction the verifier uses), parse each artifact's `raw_review`, and populate `parsed_findings` plus recomputed `p1/p2/p3` counts and `stop_rule_met`. Preserve every other field byte-for-byte. Idempotent: a second run must change nothing.
- [X] T018 Add `--dry-run` to the migration so an operator can see what a backfill would recover before writing, and print a per-file summary (`branch: N findings recovered`).
- [X] T019 Verify backfill on COPIES of live artifacts from three repos before any in-place run; confirm idempotence by running twice.

---

## Dependencies

- T001 → T002/T003 (fixtures before the verifier's assertions reference them).
- T003 (red) → T004–T008 (the fix) → T009 (green).
- T004 → T005/T006/T007 (they consume `parsed_findings`).
- Phase 4 is independent of Phase 3's internals but must follow T007 (the shape it documents/migrates).
- T015 last: it exercises everything.

## Parallel opportunities

- T011/T012/T013 are disjoint files, safe together after T007.
- T002's three fixtures are independent of each other.

## Implementation strategy

Red first (T003 must fail on missing anchors), then the single code block, then
green. Phase 3 alone is a complete, shippable fix; Phase 4 makes it durable
(migration, CI, docs). Commit at each checkpoint.
