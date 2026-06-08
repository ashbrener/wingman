---
description: "Task list for Marketplace Plugin + Pluggable Reviewer"
---

# Tasks: Marketplace Plugin + Pluggable Reviewer

**Input**: Design documents from `specs/001-marketplace-plugin-reviewer/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: INCLUDED. This repo's de-facto test harness is the GitHub Actions
`install-smoke` job plus `shellcheck`/`bash -n`/`py_compile`. The risky change
(the hook) is done test-first: smoke assertions are added and shown failing
before the hook is modified.

**Organization**: By user story (US1–US5 from spec.md), priority order.

> ⚠️ **Same-file sequencing**: US2, US3, US4 all edit `assets/pre-push.sample`.
> Tasks touching that file are NOT marked `[P]` and must run in listed order.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Verify working branch is `feat/marketplace-plugin` and required local tools exist (`git`, `python3`, `shellcheck`, and `claude plugin validate`); note any missing tool so its verification step can fall back. (no file change)

---

## Phase 2: Foundational (Blocking Prerequisites)

- [x] T002 Confirm no data migration is needed — the review record stays `wingman_schema_version: "3"` (only `reviewer.tool/provider` values and the new `reviewer_missing` status vary); record that US1 is fully independent while US2–US4 share `assets/pre-push.sample` and must be sequenced. (no file change)

**Checkpoint**: US1 may proceed immediately; US2→US3→US4 share the hook file.

---

## Phase 3: User Story 1 - Install Wingman from the marketplace (Priority: P1) 🎯 MVP

**Goal**: Wingman is installable as a Claude Code plugin and exposes `/wingman:*` commands.

**Independent Test**: `claude plugin validate . --strict` passes; from a clean Claude Code, `/plugin marketplace add ashbrener/wingman` + `/plugin install wingman` exposes the three `/wingman:*` commands.

- [x] T003 [US1] Create `.claude-plugin/plugin.json` per `specs/001-marketplace-plugin-reviewer/contracts/plugin-manifest.md` (name `wingman`, version `1.0.0`, keywords array, MIT, repo URLs).
- [x] T004 [US1] Create `.claude-plugin/marketplace.json` per the same contract (`owner`, one `plugins[]` entry with `source: "./"`).
- [x] T005 [US1] Validate: run `claude plugin validate . --strict` (exit 0, no warnings); if unavailable, fall back to a `python3 -c "import json; json.load(...)"` parse check and record that validate must run pre-submission.
- [x] T006 [P] [US1] In `README.md`, add an "Install as a Claude Code plugin" section (`/plugin marketplace add ashbrener/wingman` → `/plugin install wingman` → `/wingman:review-setup`) and note the `/wingman:*` namespace.
- [x] T007 [US1] Verify skills auto-discover: `ls skills/*/SKILL.md` resolves the three skills (become `/wingman:review-setup|review-loop|review-retro`); no file moves needed.

**Checkpoint**: Plugin is installable and listed — minimum shippable value.

---

## Phase 4: User Story 2 - Choose which model reviews my code (Priority: P1)

**Goal**: `WINGMAN_REVIEWER` (codex|gemini|claude) selects the reviewer; codex unchanged; findings flow through the existing loop unchanged.

**Independent Test**: Set each reviewer in turn, trigger a review, confirm it's produced by that model and the review record's `reviewer.tool` reflects it.

### Tests for User Story 2 (test-first) ⚠️

- [x] T008 [P] [US2] In `.github/workflows/wingman-ci.yml`, add Scenario 8 asserting the payload writes `reviewer.tool` from `WINGMAN_TOOL`, and add fresh-install asserts for `WINGMAN_REVIEWER` + `gemini|claude)`; run the new asserts locally against the current v3 hook and confirm they FAIL.

### Implementation for User Story 2 (sequential — `assets/pre-push.sample`)

- [x] T009 [US2] In `assets/pre-push.sample`, add `WINGMAN_REVIEWER` resolution with precedence env var → `.wingman-reviewer` file → `codex` (read the file, do NOT source it).
- [x] T010 [US2] In `assets/pre-push.sample`, add a `_full_prompt_file` temp (mktemp) to the `local` list and the `RETURN` trap inside `_wingman_run`.
- [x] T011 [US2] In `assets/pre-push.sample`, replace the codex-only invocation block with a `WINGMAN_REVIEWER` `case`: codex keeps native `codex review` (+model pin + fallback); `gemini|claude` build `[P1/P2/P3]` preamble + existing prompt + `git diff <base>...HEAD`, piped via **stdin**.
- [x] T012 [US2] In `assets/pre-push.sample`, replace the codex banner grep with per-reviewer metadata (`tool`, `tool_version` via `<cli> --version`, `model` = WINGMAN_MODEL or default, `provider` = openai/google/anthropic).
- [x] T013 [US2] In `assets/pre-push.sample`, export `WINGMAN_TOOL="$_tool"` into the Python heredoc env and set `reviewer.tool` from `os.environ.get("WINGMAN_TOOL") or "codex"`.
- [x] T014 [US2] In `assets/pre-push.sample`, append a non-blocking `[CROSS-MODEL NOTE]` to `notices` when `WINGMAN_REVIEWER=claude` (FR-017).
- [x] T015 [US2] In `skills/review-setup/SKILL.md`, make prerequisites reviewer-agnostic (codex default; gemini/claude via `WINGMAN_REVIEWER`) and persist the chosen repo default to `.wingman-reviewer`.
- [x] T016 [P] [US2] In `skills/review-loop/SKILL.md`, de-Codex the description + fresh-review path (use the configured reviewer; note `reviewer.tool` varies).
- [x] T017 [P] [US2] In `skills/review-retro/SKILL.md`, generalize wording and add grouping by `reviewer.tool`.
- [x] T018 [P] [US2] In `README.md`, lead with the write-back differentiator and add a `WINGMAN_REVIEWER` row to the Configuration table (generalize the `WINGMAN_MODEL` row).
- [x] T019 [US2] Static checks: `bash -n assets/pre-push.sample`, `shellcheck --severity=error --shell=bash assets/pre-push.sample`, and `py_compile` of the extracted `WINGMAN_PYEOF` heredoc — all clean.
- [x] T020 [US2] Run the Scenario 8 reviewer.tool assertion locally → PASS.

**Checkpoint**: Reviewer is selectable; codex behavior unchanged; loop reviewer-neutral.

---

## Phase 5: User Story 3 - Never get blocked when a reviewer is missing (Priority: P2)

**Goal**: A missing/unknown reviewer never blocks the push and yields a clear `reviewer_missing` record.

**Independent Test**: With the configured reviewer's CLI absent, push completes and the review record has `status: "reviewer_missing"` with a hint.

### Tests for User Story 3 (test-first) ⚠️

- [x] T021 [P] [US3] In `.github/workflows/wingman-ci.yml`, assert the fresh hook contains `WINGMAN_REVIEWER_MISSING`, and add a payload assertion that a raw review starting with `WINGMAN_REVIEWER_MISSING` yields `status: "reviewer_missing"`; confirm FAIL pre-impl.

### Implementation for User Story 3 (sequential — `assets/pre-push.sample`)

- [x] T022 [US3] In `assets/pre-push.sample`, guard the dispatch with `command -v "$WINGMAN_REVIEWER"`; on missing/unknown, write the `WINGMAN_REVIEWER_MISSING:` message (with install/switch hint) to the review file; keep the run backgrounded + `|| true` (push never blocked).
- [x] T023 [US3] In `assets/pre-push.sample` Python heredoc, set `status = "reviewer_missing"` when `raw` starts with `WINGMAN_REVIEWER_MISSING`.
- [x] T024 [P] [US3] In `skills/review-setup/SKILL.md`, detect a missing reviewer CLI and print its install hint without blocking setup.
- [x] T025 [US3] Simulate locally (`WINGMAN_REVIEWER=nonexistent`) that a push completes and a `reviewer_missing` record is written; run the T021 CI asserts → PASS.

**Checkpoint**: Cold installs degrade gracefully.

---

## Phase 6: User Story 4 - Upgrade an existing install cleanly (Priority: P2)

**Goal**: Existing v1/v2/v3 installs upgrade in place to v4 with exactly one block and no data loss.

**Independent Test**: Install an older version, run setup, confirm exactly one Wingman block at `# wingman-hook-version: 4` and prior `.reviews/` data intact.

### Tests for User Story 4 (test-first) ⚠️

- [x] T026 [P] [US4] In `.github/workflows/wingman-ci.yml`, retarget the v1→ and v2→ scenarios to v4, add a v3→v4 scenario (seed from SHA `fb82fed`), retarget `--force` to v4, bump fresh-install asserts to version `4`, and update the job name; run locally against current sample → FAIL (still v3).
- [x] T026a [P] [US4] In the v3→v4 scenario, BEFORE running the upgrade, seed prior review data — write `.reviews/2026-01-01-000000-feat-x.json` (any JSON) and `.reviews/_convergence.json` — then AFTER the upgrade assert both files still exist with unchanged contents (data-preservation for FR-010 / SC-004, not just block count).

### Implementation for User Story 4 (sequential — `assets/pre-push.sample`, then installer)

- [x] T027 [US4] In `assets/pre-push.sample`, bump `# wingman-hook-version: 3` → `4`, keep line 1 marker byte-identical, document `WINGMAN_REVIEWER` in the header, and add a v4 History entry.
- [x] T028 [US4] In `scripts/install.sh`, generalize the post-install message (line ~248) from "Codex reviews in background" to a reviewer-neutral phrasing; confirm `SAMPLE_VERSION` now auto-derives to 4 (no detection change).
- [x] T029 [US4] Run the full `install-smoke` job locally (fresh / v1→v4 / v2→v4 / v3→v4 / --force / exemptions / convergence / reviewer.tool) → all scenarios pass with exactly one block each, and the v3→v4 data-preservation assertion (T026a) passes.

**Checkpoint**: Upgrades are clean and data-preserving.

---

## Phase 7: User Story 5 - Keep working on non-Claude-Code agents (Priority: P3)

**Goal**: The skills-CLI install path is retained and unaffected.

**Independent Test**: `npx skills add ashbrener/wingman` installs the three skills for a non-Claude-Code agent.

- [x] T030 [P] [US5] In `README.md`, retain the `npx skills add` section and add a dual-command table mapping `/wingman:*` (plugin) ↔ `/review-*` (skills CLI).
- [x] T031 [US5] Verify the three `skills/*/SKILL.md` frontmatter (`name`, `description`) is intact and non-namespaced invocation still resolves.

**Checkpoint**: No regression for existing multi-agent users.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T032 [P] Remove the stray root `.wingman-exemptions.yaml.sample` (canonical copy stays at `assets/.wingman-exemptions.yaml.sample`).
- [ ] T033 Finalize `README.md`/`.gitignore`: keep `.reviews/*.json` + `.env`/`.env.local` ignores; ensure no contradictions.
- [ ] T034 Enforce packaging boundary (FR-019/D9): gitignore `.specify/` and the spec-kit `CLAUDE.md`; `git rm --cached --ignore-unmatch .specify/feature.json`; confirm `.env` stays ignored.
- [ ] T035 Run `quickstart.md` end-to-end mentally/locally: the documented install + reviewer-selection steps match the shipped behavior.
- [ ] T036 Full verification gate: `claude plugin validate . --strict`; `shellcheck --severity=error` (install.sh + pre-push.sample); `bash -n` both; `py_compile` both heredocs; full `install-smoke`.
- [ ] T037 Confirm only marketplace-relevant paths are staged (no `.specify/`, `CLAUDE.md`, `.env`); push `feat/marketplace-plugin`; open PR to `main` with summary + verification evidence.
- [ ] T038 After CI is green and the PR merges, hand off the manual marketplace submission (`claude.ai/settings/plugins/submit`) with the ready-to-paste blurb.

---

## Dependencies & Execution Order

- **Setup (P1)** → **Foundational (P2)** → **User Stories** → **Polish (P8)**.
- **US1 (P1)** is independent (manifests + README plugin section) — can ship as MVP alone.
- **US2 (P1) → US3 (P2) → US4 (P2)** must be sequenced: all edit `assets/pre-push.sample`. Within each, test task first (FAIL), then implementation, then re-run (PASS).
- **US5 (P3)** is independent (README + skills verification).
- **Polish** depends on all desired stories.

### Within `assets/pre-push.sample` (strict order)

T009 → T010 → T011 → T012 → T013 → T014 (US2) → T022 → T023 (US3) → T027 (US4).

### Parallel Opportunities

- T006 (README plugin section) ∥ T007 during US1.
- T016, T017, T018 (separate skill/README files) ∥ each other during US2 (after the hook edits land).
- T024 (review-setup) ∥ the US3 hook edits only if on a different file (it is) — but review-setup is also touched by T015; sequence T015 before T024.
- Test-authoring tasks T008/T021/T026 all touch `wingman-ci.yml` — sequence them (same file), not parallel.

---

## Implementation Strategy

### MVP

US1 alone makes Wingman installable/listable. But US1+US2 together is the
meaningful first release (installable AND the reviewer-agnostic promise is real).
Recommend shipping US1+US2+US3 (graceful cold install) as the launch cut, with
US4 (clean upgrade) close behind since existing users will hit it.

### Incremental Delivery

US1 → validate install. US2 → validate reviewer selection (codex regression-checked). US3 → validate graceful degradation. US4 → validate upgrade matrix. US5 → confirm no multi-agent regression. Polish → package boundary + PR + submission.

---

## Notes

- `[P]` = different files, no incomplete-task dependency.
- Hook edits (US2–US4) are single-file and strictly ordered.
- Every test task must be shown FAILING before its implementation tasks.
- Commit after each task or logical group; keep `.specify/`, `CLAUDE.md`, `.env` out of commits (explicit `git add` by path).
