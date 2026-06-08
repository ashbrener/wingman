# Phase 0 Research: Marketplace Plugin + Pluggable Reviewer

All decisions below resolve the Technical Context; there are no remaining
NEEDS CLARIFICATION items (the spec's `/speckit-clarify` pass resolved the open
product questions; the items here are technical/implementation choices).

## D1 — Packaging: single-repo marketplace + plugin

- **Decision**: Add both `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` at the repo root; the marketplace entry's `source` is `"./"` (the repo root is the plugin).
- **Rationale**: Lets users install immediately via `/plugin marketplace add ashbrener/wingman` → `/plugin install wingman`, independent of community-review approval, while the same repo is also submittable to the community marketplace. Skills are auto-discovered from the existing root `skills/` dir, so no files move.
- **Alternatives considered**: Community-submission-only (no direct install until approved — slower adoption); separate marketplace repo (more moving parts, splits the source of truth).

## D2 — Reviewer abstraction via a uniform output contract

- **Decision**: Introduce `WINGMAN_REVIEWER` (codex | gemini | claude). A `case` in the hook dispatches the invocation. For gemini/claude (no native review subcommand) the hook constructs a prompt whose preamble *instructs the model to emit findings as* `[P1|P2|P3] file:line (category) — description`. The existing convergence/parse logic is reused unchanged.
- **Rationale**: One downstream parser for all reviewers. Minimizes new code and keeps categorize/fix/learn reviewer-neutral (FR-006).
- **Alternatives considered**: Per-reviewer output parsers (more code, more drift); a JSON output contract (more brittle across CLIs that wrap/escape output).

## D3 — Diff handoff via stdin, not argv

- **Decision**: For gemini/claude, pipe the constructed prompt+diff via **stdin** (`< file`); codex keeps its native `--prompt-file`.
- **Rationale**: The diff can be hundreds of KB; passing it on argv risks `E2BIG` (ARG_MAX), the exact failure mode the v2 hook history records.
- **Alternatives considered**: `-p "$(cat …)"` argv (rejected — reintroduces ARG_MAX).

## D4 — Diff scope: three-dot (merge-base)

- **Decision**: `git diff "$WINGMAN_BASE"...HEAD` for the constructed reviewers.
- **Rationale**: Mirrors `codex review`'s default semantics (changes since the branch diverged from base), so findings are consistent across reviewers (FR-012).
- **Alternatives considered**: two-dot `base..HEAD` (can include unrelated upstream drift).

## D5 — Backward-compatible upgrade via a stable marker

- **Decision**: Keep the hook's first line marker byte-identical (`# --- Wingman: Codex review (non-blocking) ---`) and only bump the embedded `# wingman-hook-version: 3` → `4`.
- **Rationale**: `install.sh` detects/strips/version-compares on that marker substring. Keeping it stable means existing v1/v2/v3 installs are detected and upgraded to v4 in place with exactly one block (FR-009) and **zero installer detection changes**.
- **Alternatives considered**: Rename the marker to drop "Codex" + broaden installer detection (rejected — risk of orphaning existing installs into duplicate blocks; the marker is an internal sentinel, not user-facing).

## D6 — Default model: each CLI's own latest (clarified)

- **Decision**: When `WINGMAN_MODEL` is unset, run each reviewer with no model pin (the CLI picks its own default/latest), mirroring codex today (FR-018).
- **Rationale**: Always-current, zero maintenance; matches existing behavior.
- **Alternatives considered**: Hardcoded per-reviewer pins (needs upkeep as models ship/retire).

## D7 — Reviewer selection + persistence (clarified)

- **Decision**: Resolve `WINGMAN_REVIEWER` with precedence **env var > repo file > built-in default (codex)**. `/wingman:review-setup` persists the chosen repo default to a plain `.wingman-reviewer` file (contents = the reviewer name, e.g. `gemini`). The hook reads it without sourcing it (no code execution): capture the env value first, else read the file, else default codex.
- **Rationale**: Per-push override (env) plus a sticky repo default (file) gives the low-friction cold-install UX (FR-016) without executing repo content at push time.
- **Alternatives considered**: Sourcing a `.wingman.env` (rejected — arbitrary code execution at push time); baking the default into the hook block (rejected — regenerated on upgrade, would be lost); a full YAML config (overkill for one value).

## D8 — Same-model cross-model note (clarified)

- **Decision**: When `WINGMAN_REVIEWER=claude`, the hook appends a non-blocking notice to the review record (`[CROSS-MODEL NOTE] reviewer 'claude' may match the code author — for a true second opinion use codex or gemini`), and the Claude-side skills surface the same note. The review still runs (FR-017).
- **Rationale**: The hook cannot reliably know the code's author, but `claude` is the only reviewer that *can* coincide with the writer in the primary (Claude Code) audience, so a targeted note is correct and cheap. Non-blocking preserves the on-ramp.
- **Alternatives considered**: Detecting the writer model (not knowable from the hook); blocking same-model (rejected by clarification — it's a valid on-ramp).

## D9 — Packaging boundary excludes local tooling/secrets (clarified)

- **Decision**: The published plugin ships only plugin-relevant files. `.specify/`, the linear extension, the spec-kit `CLAUDE.md`, and `.env` are excluded (gitignored / not committed to the plugin) (FR-019).
- **Rationale**: This repo now also hosts local spec-kit/linear dev tooling and a local secret; none of it belongs in a public marketplace package.
- **Alternatives considered**: Rely on `.gitignore` alone (riskier — easy to accidentally `git add` scaffolding).

## D10 — Submission target

- **Decision**: Submit to the **community** marketplace via the web form (`claude.ai/settings/plugins/submit`); document it as a manual maintainer step.
- **Rationale**: The official/curated marketplace is selected by Anthropic at its discretion with no application; community is the actionable path.
- **Alternatives considered**: None viable for self-submission.
