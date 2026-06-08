# Implementation Plan: Marketplace Plugin + Pluggable Reviewer

**Branch**: `feat/marketplace-plugin` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-marketplace-plugin-reviewer/spec.md`

## Summary

Package Wingman as a Claude Code marketplace plugin (add `.claude-plugin/plugin.json` + a single-repo `.claude-plugin/marketplace.json`; skills auto-discovered from the existing `skills/`) and make the reviewer genuinely pluggable via `WINGMAN_REVIEWER` (codex default | gemini | claude). The Codex path is preserved unchanged; gemini/claude get a constructed diff+prompt with a uniform `[P1/P2/P3]` output contract so the downstream categorize/fix/learn loop is reviewer-neutral. A repo-default reviewer is persisted at setup, overridable per-push by the env var. Missing/erroring reviewers degrade gracefully (push never blocked; `reviewer_missing` record). Same-model selection runs but emits a non-blocking cross-model note. Hook version bumps 3→4 with a byte-stable marker for in-place auto-upgrade. README/skills are de-Codex'd; the README leads with the write-back differentiator. The published package excludes local tooling/secrets.

## Technical Context

**Language/Version**: Bash (must run on macOS bash 3.2 *and* GNU/Linux); Python 3 (embedded heredocs, stdlib only); JSON (manifests + review records); Markdown (skills/docs).

**Primary Dependencies**: `git`; one reviewer CLI — `codex` (default), `gemini`, or `claude` (all external + optional); `gh` (optional, CI-status awareness); the Claude Code plugin system (marketplace + skill discovery). The `skills` CLI (`npx skills add`) remains the alternate install path.

**Storage**: Files only — `.reviews/<ts>-<branch>.json` (review records), `.reviews/_convergence.json` (round ledger), `.claude/rules/review-patterns.md` (learned patterns), the persisted repo-default reviewer, and the pre-push hook block.

**Testing**: `shellcheck --severity=error` (install.sh + pre-push.sample), `bash -n`, `py_compile` of the extracted heredocs, the GitHub Actions `install-smoke` scenario matrix, and `claude plugin validate [--strict]`.

**Target Platform**: Developer machines (macOS + Linux); Claude Code (plugin) and 45+ agents (skills CLI). CI runs on Linux (authoritative).

**Project Type**: Developer tooling — a Claude Code plugin composed of skills + a git pre-push hook + an installer. Not an application; no app server/UI.

**Performance Goals**: Push returns immediately (review is backgrounded, non-blocking). A review typically completes in ~60–120s depending on reviewer; wall time is recorded per review.

**Constraints**: Push MUST NEVER be blocked by a reviewer (missing/erroring/slow). Reviewer input MUST be passed via stdin/prompt-file, never argv (ARG_MAX safety — the diff can be hundreds of KB). Hook upgrade MUST be backward-compatible (existing v1/v2/v3 installs → v4, exactly one block). No secrets or local tooling in the published package.

**Scale/Scope**: One plugin, 3 skills, one hook, one installer, one CI workflow. Single-maintainer repo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` is an **unratified template** (placeholder principles only) — there are no project-specific gates to enforce. **Result: PASS (no gates).**

The de-facto engineering norms inherited from the existing codebase are honored by this plan and worth stating:
- **Backward compatibility**: hook upgrades are in-place and non-destructive (FR-009/FR-010).
- **Test-first for the risky change**: CI smoke assertions for v4 + reviewer dispatch are written and shown failing before the hook is modified.
- **Zero-regression default**: the codex path is byte-for-byte unchanged (FR-005).
- **Cross-platform shell**: bash 3.2 + GNU; CI Linux is authoritative.

*Recommendation (non-blocking): run `/speckit-constitution` later to ratify these norms so future features inherit explicit gates.*

**Post-Phase-1 re-check**: PASS — the design introduces no new violations (no new project, no added abstraction layers; the reviewer dispatch is one bounded `case` plus per-reviewer metadata).

## Project Structure

### Documentation (this feature)

```text
specs/001-marketplace-plugin-reviewer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
│   ├── plugin-manifest.md   # plugin.json + marketplace.json + validation
│   ├── reviewer-config.md   # WINGMAN_REVIEWER + output contract + failure modes
│   └── upgrade.md           # in-place v1/v2/v3 → v4 invariants
│   # (review-record shape lives in data-model.md)
├── checklists/
│   └── requirements.md  # from /speckit-specify
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
.claude-plugin/
├── plugin.json              # NEW — plugin manifest (name "wingman", v1.0.0)
└── marketplace.json         # NEW — single-repo marketplace listing

skills/                      # EXISTING — auto-discovered as /wingman:*
├── review-setup/SKILL.md    # MODIFY — reviewer-agnostic prereqs; persist repo default
├── review-loop/SKILL.md     # MODIFY — de-Codex; reviewer-neutral fresh-review path
└── review-retro/SKILL.md    # MODIFY — group by reviewer.tool

assets/
├── pre-push.sample          # MODIFY — WINGMAN_REVIEWER dispatch + metadata + v4
└── .wingman-exemptions.yaml.sample   # EXISTING (canonical) — unchanged

scripts/
├── install.sh               # MODIFY — generalize message; persist repo default; version auto-derives
└── migrate-reviews.py       # EXISTING — unchanged

.github/workflows/
└── wingman-ci.yml           # MODIFY — v4 + reviewer-dispatch + reviewer.tool smoke assertions

README.md                    # MODIFY — lead with write-back; dual install; WINGMAN_REVIEWER
.gitignore                   # MODIFY — finalize; keep .env hygiene; drop local-tooling lines from publish
./.wingman-exemptions.yaml.sample   # REMOVE — stray root duplicate
```

**Structure Decision**: Keep the existing flat tool layout (no `src/`). The plugin manifest lives in `.claude-plugin/`; everything else is the established `assets/` + `scripts/` + `skills/` structure. The only structural addition is `.claude-plugin/`. Local spec-kit/linear scaffolding (`.specify/`, linear extension, `.env`) is excluded from the published package (FR-019).

## Complexity Tracking

No constitution violations — section intentionally empty.
