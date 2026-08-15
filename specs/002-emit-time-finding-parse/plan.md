# Implementation Plan: Findings parsed at emit time

**Branch**: `fix/emit-time-finding-parse` | **Date**: 2026-08-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-emit-time-finding-parse/spec.md`

## Summary

Parse the reviewer's findings when the artifact is written, so the artifact
reflects what the reviewer found. A new `parsed_findings` array carries the
machine-readable findings (leaving `findings` as the review loop's
categorization target), and every priority count — and therefore the stop-rule
and its convergence recommendation — derives from the MAX of the native parse
and the legacy priority grep, so neither supported output shape can be zeroed by
the other and no future format change can silently blind the signal again.
Decisions in [research.md](research.md) (R-1 … R-7).

## Technical Context

**Language/Version**: Bash + inline Python 3 (stdlib only), as today

**Primary Dependencies**: none added — `re` and `json` already imported in the
existing heredoc

**Storage**: the review artifact JSON under `.reviews/` and its
`_convergence.json` ledger — shapes extended, locations unchanged

**Testing**: `scripts/verify-parser.py` extracts the parser from the hook
between unique anchors and runs it against four recorded fixtures (R-7); wired
into `.github/workflows/wingman-ci.yml`

**Target Platform**: any repo installing the hook (macOS/Linux, git ≥ 2.9)

**Project Type**: git-hook + skills pack (single artifact: `assets/pre-push.sample`)

**Performance Goals**: parsing is a line scan over one review; the hook stays
backgrounded and never blocks a push

**Constraints**: no new dependency · parser single-sourced in the hook (no copy)
· reviewer-missing and CI-red synthetic paths unchanged · older artifacts remain
readable

**Scale/Scope**: one file changed for behaviour, plus the migration script, the
verifier, fixtures, CI, and the two SKILL docs that describe the artifact shape

## Constitution Check

*GATE: `.specify/memory/constitution.md` in this repo is **an unratified
template** — every principle is still a `[PRINCIPLE_N_NAME]` placeholder. There
is therefore no project-specific gate to evaluate, and this plan records that
honestly rather than claiming a pass against placeholders.*

Applying the pack's own published discipline instead (`skills/review-loop`):

- **Review is advisory, never blocking** — unchanged: the hook still backgrounds
  and never fails a push. PASS.
- **Findings are surfaced, not auto-resolved** — the feature only makes findings
  legible; categorization and routing stay human/agent decisions. PASS.
- **Single source of truth** — the parser exists once, in the hook; the verifier
  extracts rather than copies it. PASS.

**Follow-up (out of scope here, worth its own round)**: wingman ships review
discipline to other repos while its own constitution is unfilled. Recorded in
this plan so it is not lost.

## Project Structure

### Documentation (this feature)

```text
specs/002-emit-time-finding-parse/
├── plan.md                 # this file
├── research.md             # R-1 … R-7
├── data-model.md           # parsed finding, round summary, artifact
├── quickstart.md           # replay the incident; verify a clean review
├── contracts/
│   └── review-artifact-v4.md   # the emitted shape + parsing contract
└── tasks.md                # /speckit-tasks output
```

### Source (repository root)

```text
assets/pre-push.sample            # the ONLY behavioural change:
                                  #   + anchored parser block
                                  #   + counts from MAX(native, legacy)
                                  #   + finding ids include file:line
                                  #   + emit parsed_findings, schema 4
                                  #   + marker → wingman-hook-version: 5
scripts/migrate-reviews.py        # + 3→4 step (adds empty parsed_findings)
scripts/verify-parser.py          # NEW — extracts + exercises the parser
tests/fixtures/
├── incident-native.txt           # the recorded 3-finding codex review
├── legacy-priority.txt           # [P1]/[P2] shape
├── no-findings.txt               # honest zero
└── prose-with-pipes.txt          # false-positive guard
.github/workflows/wingman-ci.yml  # + verifier step
skills/review-loop/SKILL.md       # artifact shape: document parsed_findings
skills/review-setup/SKILL.md      # hook version reference → 5
```

**Structure Decision**: single-artifact repo; the behavioural change is confined
to the hook sample, with the verifier as the only new executable.

## Design decisions (binding for /speckit-tasks)

- **D1** (R-1): `parsed_findings` is additive; `findings`/`resolutions` untouched.
- **D2** (R-2): `p{1,2,3}_count = max(native, legacy)` — the anti-regression property.
- **D3** (R-3): `critical|high→P1`, `medium→P2`, `low→P3`.
- **D4** (R-4): a line qualifies only with BOTH closed vocabularies present.
- **D5** (R-5): stagnation ids gain `file:line`, appended to existing heuristics.
- **D6** (R-6): schema 3→4, hook marker 4→5, migration step added.
- **D7** (R-7): parser fenced by unique anchor comments; verifier asserts anchor
  uniqueness, execs the block, runs four fixtures; CI runs the verifier.
- **D8**: the convergence notice text is unchanged — it simply can no longer fire
  while findings exist, because its inputs are now true.

## Phase 0 → 1 outputs

- [research.md](research.md) — complete
- [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)
