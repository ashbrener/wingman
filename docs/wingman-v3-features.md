# Wingman v3 features

Wingman v3 adds four upgrades to the codex-review pre-push hook. These were direct lessons from a 12-round wingman convergence on `project-arc` spec 004 — every gap below was felt for several rounds before being addressed.

| # | Feature | Lesson it addresses |
|---|---|---|
| 1 | Exemption file (`.wingman-exemptions.yaml`) | Codex re-flagged ratified out-of-scope decisions for ~3 rounds in a row. |
| 2 | CI status awareness | The required status check `quality-gate` was red for 12 rounds while wingman insisted everything was green. |
| 3 | Round tracking + convergence detection | No "are we done yet?" signal — the loop ran 12 rounds without a stop-rule trigger. |
| 4 | Audit-related-paths in the codex prompt | A fix landed; codex flagged a bug in the fix the next round; the bug shared a defect class with neighbouring code that was never reviewed. |

The hook version stamp bumps from `2` → `3`. Re-running the installer (`bash scripts/install.sh` or `/review-setup`) upgrades any pre-v3 hook in place.

---

## Feature 1 — Exemption file

**File**: `<repo>/.wingman-exemptions.yaml` (user-managed; not auto-created).
**Sample**: shipped at `assets/.wingman-exemptions.yaml.sample` and copied to `<repo>/.wingman-exemptions.yaml.sample` by the installer.
**Override path**: set `WINGMAN_EXEMPTIONS=<path>` to point elsewhere (e.g. `docs/exemptions/codex.yaml`).

Each exemption documents an out-of-scope decision and the artefact that ratified it. The hook reads the file on each push, parses it (`yaml.safe_load` if PyYAML is available, otherwise a tiny inline line-parser that handles the documented sample shape), and renders a system-context block into the codex prompt:

```
EXEMPTIONS (do NOT surface these as unaddressed findings):
  1. id=shim-files-flat-paths
     pattern: preserve old top-level paths via shim files|flat path shim
     rationale: Constitution v0.1.3 directory-as-namespace rule rejects ...
     referenced_by: constitution.md L227-234
  ...
If a finding matches an exemption pattern, either skip it OR tag it
with 'EXEMPT (per rationale: <id>)' instead of as an unaddressed finding.
```

The list of exemption `id`s also lands in the review payload at `.exemptions[]` so downstream tools (e.g. `/review-loop`) can show "this round suppressed N exemptions."

### Schema

```yaml
exemptions:
  - id: "kebab-case-id"             # short stable identifier
    pattern: "regex|alternation"     # case-insensitive; matched against finding text
    rationale: "Single-line why."    # surfaced verbatim to codex
    referenced_by: "doc#L1-L5"       # pointer to ratifying artefact
```

When in doubt, prefer fixing the underlying issue over adding an exemption. Exemptions exist for ratified out-of-scope decisions — not for "we'll get to it later."

---

## Feature 2 — CI status awareness

After the codex review completes, the hook resolves the branch's PR (`gh pr list --head <branch> --json number --jq '.[0].number'`) and calls `gh pr checks <pr> --json name,state,link`. The result lands in the review payload at `.ci_status`:

```jsonc
"ci_status": {
  "state": "FAILURE",                // SUCCESS | PENDING | FAILURE | NONE | UNKNOWN
  "checks": [ { "name": "quality-gate", "state": "FAILURE", "link": "https://..." } ],
  "pr_number": "42",
  "failing": [ { "name": "quality-gate", "state": "FAILURE", "link": "https://..." } ]
}
```

If the PR doesn't exist yet (no PR for the branch, or `gh` not installed), the hook degrades to `state: "NONE"` and continues — no error, no synthetic finding.

When `failing[]` is non-empty, the hook prepends a synthetic P1 finding to `raw_review` and surfaces it in `.synthetic_findings[]`:

```
[P1] CI status: quality-gate = FAILURE — investigate and fix before continuing
wingman convergence. (https://github.com/.../runs/123456789)
```

This way the next remediation iteration sees CI red as a P1 and addresses the failing check instead of bandaging code that's locally green but CI red.

---

## Feature 3 — Round tracking + convergence detection

**Ledger file**: `<repo>/.reviews/_convergence.json` (gitignored — runtime state, like `.reviews/<timestamp>.json`).

After each review, the hook appends a row:

```jsonc
{
  "branch": "004-upgrade-and-apply-to-existing",
  "rounds": [
    {
      "round": 1,
      "timestamp": "2026-04-29T15:08:26Z",
      "review_file": "2026-04-29-150826-...json",
      "p1_count": 2,
      "p2_count": 2,
      "p3_count": 0,
      "ci_status": "FAILURE",
      "finding_ids": ["import-path-shim", "uvx-synthetic-base"]
    }
  ],
  "convergence": {
    "stop_rule_met_at_round": null,
    "consecutive_zero_p1_rounds": 0,
    "stagnation_detected": false,
    "stagnation_ids": [],
    "trend": "n/a"
  }
}
```

Severity counts come from regex-counting `[P1]/[P2]/[P3]` and `Priority N` markers in the codex output. Synthetic CI-red findings count toward `p1_count`.

### Stop-rule (RESUME §4 rule 12)

When the last 2 rounds both have `0` P1 findings and `≤2` P2 findings, the hook stamps `stop_rule_met_at_round` and prepends a notice to the review payload (`.notices[]` and `raw_review`):

```
[CONVERGENCE NOTICE] Round 8: 0 P1 + 2 P2 — convergence stop-rule met (per
RESUME §4 rule 12). The remaining P2 findings can be exempted with documented
rationale per constitution v0.1.2 exemption type 3. Recommend declaring
convergence and updating PR body.
```

### Stagnation alert

If the same finding ID appears in 2 consecutive rounds, the hook emits:

```
[STAGNATION ALERT] Round N: finding(s) <id-1>, <id-2> flagged in 2 consecutive
rounds. Fix isn't sticking; manual investigation needed.
```

Finding IDs are extracted heuristically from `[P1] <id>:` and `Finding <id>:` patterns in codex output.

### Trend

Each round records a `trend` value (`converging` / `flat` / `diverging` / `n/a`) computed from the change in `p1_count + p2_count` versus the previous round.

---

## Feature 4 — Audit-related-paths prompt

The hook builds a richer codex prompt that asks the reviewer to audit not just the diff but also code paths that import from / are imported by the changed modules — and to surface same-class defects in the same review:

> Review the diff against `<base>`. ALSO audit any code paths whose touched files import from, or are imported by, the changed modules. If you find issues in those related paths that share the same defect class as a finding in the diff, surface them in the same review (don't wait for the next round).
>
> Examples of related-path audits:
> - If the diff touches `services/upgrade/`, audit `commands/apply.py`, `commands/upgrade.py`, `services/scaffold/` for the same kinds of bugs.
> - If the diff touches snapshot/restore logic, audit ALL snapshot-write call sites + ALL restore-call sites.

The prompt is written to a temp file and passed via `codex review --prompt-file <path>`. If the installed codex CLI doesn't support `--prompt-file`, the hook falls back to the v2-style invocation with no prompt file — guaranteeing v3 never regresses behaviour for older codex installs.

This is a prompt-engineering change, not a code change. Bigger per-round prompts close more findings per round → fewer total rounds.

---

## Schema bump (`wingman_schema_version: "3"`)

Review payloads now carry:

| Field | Type | Notes |
|---|---|---|
| `wingman_schema_version` | `"3"` | bumped from `"2"` |
| `ci_status` | object | Feature 2 — `gh pr checks` snapshot |
| `convergence` | object | Feature 3 — round-level summary (counts, stop-rule, trend) |
| `exemptions` | string[] | Feature 1 — IDs of exemptions in scope this round |
| `synthetic_findings` | string[] | Feature 2 — synthetic P1 findings (CI red, etc.) |
| `notices` | string[] | Feature 3 — convergence / stagnation notices |
| `raw_review` | string | Codex output, with synthetic findings + notices prepended |

Older v2 review files keep working — `scripts/migrate-reviews.py` upgrades them in place.

---

## Upgrade flow

The installer's idempotent block-replacer detects v2 in any project that has wingman installed and upgrades in place to v3:

```
$ bash scripts/install.sh
Pre-push hook: Upgraded Wingman block (v2 → v3).
Copied: /path/to/repo/.wingman-exemptions.yaml.sample
  (rename to .wingman-exemptions.yaml to activate; v3 hook reads it on push)
Updated: .gitignore (added _convergence.json)
```

Same path that worked for v0/v1 → v2 in the prior release. `--force` re-stamps in place without bumping.
