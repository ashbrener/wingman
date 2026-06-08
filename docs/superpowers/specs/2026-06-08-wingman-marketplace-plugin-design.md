# Wingman → Claude Code Marketplace Plugin — Design

**Date:** 2026-06-08
**Branch:** `feat/marketplace-plugin`
**Status:** Approved design, pending spec review

## Goal

Publish Wingman as an installable Claude Code plugin on the community
marketplace, positioned to beat existing code-review plugins. Two strands:

1. **Packaging** — make the repo a Claude Code plugin *and* a single-repo
   marketplace, so users can install it directly today and via
   `@claude-community` after review.
2. **Make the reviewer truly pluggable** — the repo currently *claims*
   "reviewer-agnostic" but the implementation is hardwired to Codex. This is
   the load-bearing fix for cold installs and makes the pitch honest.

Scope is deliberately bounded: packaging + reviewer abstraction + README
repositioning + housekeeping. **No** other new features (no on-demand review
command, no stop-hook trigger) — those are the post-launch backlog.

## Context: competitive position

Recon (background agent, 2026-06-08) confirmed the wedge is unoccupied:

| Competitor | Cross-model | Learning write-back | Convergence | CI aware |
|---|---|---|---|---|
| `claude-review-loop` (Hamel) | ✅ | ❌ | ❌ | ❌ |
| `codex-plugin-cc` (OpenAI) | ✅ | ❌ | ❌ | ❌ |
| Anthropic `/code-review` | ❌ | ❌ | ❌ | ❌ |
| **Wingman** | ✅ | ✅ | ✅ | ✅ |

No review plugin combines cross-model review with **writing accepted findings
back into `.claude/rules/` + linter config** ("makes itself progressively
unnecessary"). README/marketplace blurb must **lead with the write-back**, not
cross-model (rivals already have cross-model).

Naming: `brenbuilds1/claude-wingman` exists (unrelated satirical dating skills,
not on any marketplace). No *review* plugin named wingman exists. Ship as plugin
name **`wingman`**; avoid the `claude-wingman` slug.

## Decisions (locked with user)

- Plugin name / namespace: **`wingman`** → `/wingman:review-setup`,
  `/wingman:review-loop`, `/wingman:review-retro`.
- Distribution: **keep both** the new plugin path and the existing
  `npx skills add ashbrener/wingman` path (serves 45+ non-CC agents).
- Reviewer: **truly pluggable**, **Codex stays default**.
- First-class reviewers this release: **codex (default), gemini, claude**.
- Constructed-diff scope for gemini/claude: **three-dot `<base>...HEAD`**
  (merge-base), to mirror `codex review` semantics.
- Plugin version: **`1.0.0`**. Hook version: **bump 3 → 4** (auto-upgrades v3
  installs to the pluggable block).

## Component 1 — Plugin + marketplace manifests

### `.claude-plugin/plugin.json`

Only `name` is required; we add discovery/attribution metadata. Unknown fields
are warnings only, but we stick to documented fields so `--strict` passes.

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "wingman",
  "displayName": "Wingman",
  "version": "1.0.0",
  "description": "Cross-model code review that deletes its own findings. A different AI model reviews your diff on push; accepted findings are encoded back into your project rules and linter config so the same mistake can't recur.",
  "author": { "name": "Ash Brener", "url": "https://github.com/ashbrener" },
  "homepage": "https://github.com/ashbrener/wingman",
  "repository": "https://github.com/ashbrener/wingman",
  "license": "MIT",
  "keywords": ["code-review", "cross-model", "review", "linting", "git-hook", "code-quality", "self-improving"]
}
```

Skills are auto-discovered from the existing root `skills/` dir — **no file
moves, no `skills` field needed.**

### `.claude-plugin/marketplace.json`

Single-repo marketplace pointing at the root as the plugin source, so
`/plugin marketplace add ashbrener/wingman` → `/plugin install wingman` works
immediately, independent of community-review approval.

```json
{
  "name": "wingman",
  "owner": { "name": "Ash Brener", "url": "https://github.com/ashbrener" },
  "plugins": [
    {
      "name": "wingman",
      "source": "./",
      "description": "Cross-model code review that learns from every review and makes itself progressively unnecessary."
    }
  ]
}
```

Both manifests verified with `claude plugin validate` (and `--strict`) before
PR. Exact marketplace.json field set re-checked against the plugin-marketplaces
reference during implementation.

## Component 2 — Pluggable reviewer (`assets/pre-push.sample`)

### What stays untouched (already reviewer-neutral)

Exemptions parsing, CI awareness (`gh pr checks`), round-tracking/convergence,
the entire Python JSON-assembly block — all neutral. The **only** Codex
coupling is: the invocation (L154-163), the stdout-banner metadata grep
(L183-189), the hardcoded `"tool": "codex"` (L449), and the `WINGMAN_MODEL`
comment (L13).

### New env var

- `WINGMAN_REVIEWER` — `codex` (default) | `gemini` | `claude`.
- `WINGMAN_MODEL` — generalized: "pin a model for the selected reviewer."

### Dispatch: `_wingman_invoke_reviewer`

A shell function that, given `$_prompt_file`, `$WINGMAN_BASE`,
`$WINGMAN_MODEL`, writes the review to `$_review_file`:

- **codex** → unchanged. Native `codex review --base … [--prompt-file …]` with
  the existing model-pin + fallback chain. **Zero regression.**
- **gemini / claude** → no native review subcommand, so construct the input:
  1. A review-instruction preamble (see "uniform output contract").
  2. The existing audit-related-paths + exemptions prompt (`$_prompt_file`).
  3. `git diff "$WINGMAN_BASE"...HEAD` (three-dot).
  Pipe the concatenation through headless mode:
  - gemini: `gemini [-m "$WINGMAN_MODEL"] -p -` (prompt on stdin) `> $_review_file 2>&1`
  - claude: `claude -p [--model "$WINGMAN_MODEL"] > $_review_file 2>&1` (prompt on stdin)
  Exact non-interactive flags verified against each CLI's `--help` during
  implementation; both invocations end with `|| true` so the push never breaks.

### Uniform output contract (the key trick)

The downstream convergence parser (L312-331) and `/review-loop` already parse
`[P1]`/`[P2]`/`[P3]` + `file:line` + category. The constructed gemini/claude
preamble **instructs the model to emit findings in exactly that format**:

```
You are a code reviewer. Review the diff below. For EACH finding, output one line:
  [P1|P2|P3] <file>:<line> (<category: logic|security|architecture|lint>) — <one-line description>
Use [P1] critical, [P2] should-fix, [P3] nit. If no issues, output "No findings."
```

One parser serves all three reviewers — no per-reviewer downstream parsing.

### Per-reviewer metadata

Replace the single Codex banner grep with a small dispatch:

- **codex** → existing greps (`^OpenAI Codex`, `^model:`, …).
- **gemini** → `tool=gemini`, `tool_version=$(gemini --version 2>/dev/null)`,
  `model = $WINGMAN_MODEL or "default"`, `provider=google`, session/reasoning null.
- **claude** → `tool=claude`, `tool_version=$(claude --version 2>/dev/null)`,
  `model = $WINGMAN_MODEL or "default"`, `provider=anthropic`, session/reasoning null.

Pass `WINGMAN_REVIEWER` into the Python block; set JSON `reviewer.tool` from it
(replaces hardcoded `"codex"`). Output schema stays `wingman_schema_version: "3"`
— the only change is `reviewer.tool`/`provider` now vary, which existing
consumers already read dynamically.

### Cold-install safety

Before dispatch, `command -v "$reviewer"`. If absent, skip the model call and
write a review JSON with `status: "reviewer_missing"` and a `raw_review`
explaining: *"Reviewer '<x>' not found. Install it or set WINGMAN_REVIEWER to
codex|gemini|claude."* Push stays backgrounded and succeeds regardless.

### Hook header

Bump `# wingman-hook-version: 3` → `4`. Update the header comment block:
document `WINGMAN_REVIEWER`, generalize the "sync review" example and the
`WINGMAN_MODEL` line, add a v4 history entry.

## Component 3 — Skills de-Codex'd

- **review-setup/SKILL.md**: Prerequisites become "choose a reviewer (codex
  default; gemini or claude also supported via `WINGMAN_REVIEWER`)". Detect
  which reviewer CLIs are present; if the chosen one is missing, give its
  install hint (codex: `npm i -g @openai/codex`; gemini/claude: their installs).
  Drop the hard `codex-plugin-cc` / `/codex:rescue` requirement. Keep Codex as
  the documented default.
- **review-loop/SKILL.md**: Description "Run Codex cross-model review" → "Run
  cross-model review". Fresh-review path (L35 `/codex:rescue`) → "use the
  configured reviewer (`WINGMAN_REVIEWER`, default codex)". Schema example notes
  `tool` varies.
- **review-retro/SKILL.md**: "codex performance" → "reviewer performance";
  group-by-`reviewer.tool` as well as `reviewer.model`.

Note: same SKILL.md files serve the namespaced plugin (`/wingman:review-loop`)
and the non-namespaced `npx skills` channel (`/review-loop`). Prose refers to
skills by role ("the review-loop skill") rather than hardcoding one slash form
where it would mislead.

## Component 4 — README repositioning + dual install

- **Lead with the wedge**: headline the write-back / "deletes its own findings"
  + convergence-to-zero story before cross-model.
- **Add "Install as a Claude Code plugin"** section:
  `/plugin marketplace add ashbrener/wingman` → `/plugin install wingman`,
  then `/wingman:review-setup`. Keep the existing `npx skills add` section.
- **Document `WINGMAN_REVIEWER`** in the Configuration table (codex|gemini|claude).
- Update the command references to show both the `/wingman:*` (plugin) and
  `/review-*` (skills CLI) forms where relevant.

## Component 5 — Housekeeping

- Keep the `.gitignore` improvement (`.reviews/*.json`, `_convergence.json`).
- Remove the stray root `.wingman-exemptions.yaml.sample` (canonical copy is
  tracked at `assets/.wingman-exemptions.yaml.sample`).

## Testing & validation

- `claude plugin validate` and `claude plugin validate --strict` pass.
- `bash -n assets/pre-push.sample` and `scripts/install.sh` clean; `shellcheck
  --severity=error` clean (matches existing CI `lint` job).
- Extend `.github/workflows/wingman-ci.yml` `install-smoke` for the v3→v4
  upgrade path and assert the single Wingman block ends at
  `# wingman-hook-version: 4`.
- Reviewer dispatch sanity: with `WINGMAN_REVIEWER=codex` the invocation/output
  is byte-for-byte the prior behavior (regression guard). gemini/claude paths
  exercised with a stubbed CLI in the smoke test if feasible; otherwise the
  `reviewer_missing` branch is asserted.

## Delivery

`feat/marketplace-plugin` → PR → merge to `main`. **Submission is a web form**
(`claude.ai/settings/plugins/submit`) only the maintainer can complete — hand
off exact steps + a ready-to-paste blurb at the end.

## Out of scope (post-launch backlog)

On-demand `/wingman:review` command; stop-hook trigger option; Claude-as-default
zero-dep on-ramp; `wingman stats` convergence graph; consuming `codex-plugin-cc`
output as a reviewer source.
