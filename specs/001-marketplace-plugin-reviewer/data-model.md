# Phase 1 Data Model

Wingman is file-based; "entities" are config files and JSON records, not a DB.

## Plugin manifest (`.claude-plugin/plugin.json`)

| Field | Type | Notes |
|---|---|---|
| `name` | string | `wingman` — namespace for `/wingman:*` commands. Required. |
| `version` | string | `1.0.0` — semver; bump to ship updates. |
| `displayName` | string | `Wingman`. |
| `description` | string | Leads with the write-back differentiator. |
| `author` / `homepage` / `repository` / `license` | string/object | Attribution; repo `github.com/ashbrener/wingman`; MIT. |
| `keywords` | string[] | Discovery tags. Must be an array (type error otherwise). |

**Validation**: `claude plugin validate --strict` passes (no errors, no unrecognized-field warnings).

## Marketplace listing (`.claude-plugin/marketplace.json`)

| Field | Type | Notes |
|---|---|---|
| `name` | string | `wingman`. |
| `owner` | object | `{ name, url }`. |
| `plugins[]` | array | One entry: `{ name: "wingman", source: "./", description }`. `source: "./"` = repo root is the plugin. |

## Reviewer (logical)

The model producing a second-opinion review. Selected by the user; distinct from the code's author.

| Attribute | Values | Source |
|---|---|---|
| `tool` | `codex` \| `gemini` \| `claude` | `WINGMAN_REVIEWER` |
| `model` | reviewer-specific or "default" | `WINGMAN_MODEL` (unset → CLI's latest) |
| `provider` | `openai` \| `google` \| `anthropic` | derived from `tool` |

**Resolution precedence** (D7): `WINGMAN_REVIEWER` env var → `.wingman-reviewer` file → `codex`.

## Reviewer config file (`.wingman-reviewer`)

- **Content**: a single token — the reviewer name (`codex` | `gemini` | `claude`).
- **Lifecycle**: written by `/wingman:review-setup` when the user picks a repo default; read (not sourced) by the hook; safe to commit (no secret) so collaborators inherit the default.

## Review record (`.reviews/<timestamp>-<branch>.json`)

Schema **unchanged at `wingman_schema_version: "3"`**; only values vary.

| Field | Type | Change |
|---|---|---|
| `reviewer.tool` | string | NOW reflects `WINGMAN_REVIEWER` (was hardcoded `codex`). |
| `reviewer.provider` | string | NOW `openai`/`google`/`anthropic` per reviewer. |
| `reviewer.model` / `tool_version` / `wall_seconds` | string/int | Per-reviewer extraction. |
| `status` | enum | Adds `reviewer_missing` to existing `needs_categorization` / `clean` / `categorized`. |
| `notices` | string[] | MAY include the `[CROSS-MODEL NOTE]` when reviewer = claude. |
| `ci_status` / `convergence` / `exemptions` / `synthetic_findings` / `findings` / `resolutions` | (unchanged) | Reviewer-neutral. |

**Status transitions**: `reviewer_missing` (no review produced) → user installs/switches reviewer → next push produces `needs_categorization` → `/wingman:review-loop` → `categorized`. `clean` when the reviewer returned no findings.

## Convergence ledger (`.reviews/_convergence.json`)

Unchanged (round tracking, stop-rule, stagnation). Reviewer-neutral.

## Learned patterns (`.claude/rules/review-patterns.md`)

Unchanged. The write-back target — accepted findings are encoded here (and into linter config) so they don't recur. Reviewer-neutral.
