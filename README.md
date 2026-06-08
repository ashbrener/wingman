# Wingman

**The code review tool that deletes its own findings.** A different AI model
reviews your diff on every push — then every finding you accept is encoded back
into your project's rules and linter config, so the same mistake can't recur.
Reviews trend toward empty. Wingman makes itself progressively unnecessary.

Other tools review. Wingman *learns* — cross-model review + write-back +
convergence tracking in one pre-push loop.

## Why cross-model?

The model that writes your code has blind spots — it follows its own patterns and won't catch its own mistakes. A different model reviews from first principles, catching things the first model would never flag on itself.

For example: if Claude Opus writes your code, use Codex (GPT) as the reviewer. If Gemini writes your code, use Claude as the reviewer. The point is **the reviewer is a different model than the writer** — that's where the value comes from.

Wingman ships with [Codex](https://github.com/openai/codex) as the default reviewer. `/review-setup` will install it for you if it's not already present.

## Install

**As a Claude Code plugin (recommended):**

```bash
/plugin marketplace add ashbrener/wingman
/plugin install wingman
/wingman:review-setup
```

**As skills for any agent (45+ supported):**

```bash
npx skills add ashbrener/wingman
/review-setup
```

Either way you get three review capabilities:

| Skill | Plugin command | Skills-CLI command | Purpose |
|---|---|---|---|
| `review-setup` | `/wingman:review-setup` | `/review-setup` | Install git hook, `.reviews/` dir, and patterns rule file |
| `review-loop` | `/wingman:review-loop` | `/review-loop` | Review → categorize → fix → encode learned patterns |
| `review-retro` | `/wingman:review-retro` | `/review-retro` | Weekly retrospective — trends, pruning, automation recs |

## Quick start

```bash
# 1. Install skills (supports 45+ AI coding agents)
npx skills add ashbrener/wingman                # all agents
npx skills add ashbrener/wingman -a <agent>     # specific agent only

# 2. Run setup — installs git hook, .reviews/, rules file
#    Checks for reviewer CLI and installs if missing
/review-setup

# 3. Work on your feature branch, commit, push
#    Cross-model review runs in background after push — you keep working
#    The agent auto-surfaces the findings table in chat ~60-120s later;
#    no need to invoke /review-loop manually.

# 4. If the agent misses the auto-surface (or you want to re-open findings):
/review-loop

# 5. Weekly, run a retrospective
/review-retro
```

`/review-setup` is idempotent — safe to run multiple times. It detects your hooks directory (`.git-hooks/`, `.githooks/`, `.husky/`, or `.git/hooks/`) and appends to existing pre-push hooks rather than overwriting.

### Upgrades

The Wingman block in your `pre-push` hook carries a `# wingman-hook-version: N` stamp (currently `3`). Re-running the installer — `bash scripts/install.sh`, `npx skills add ashbrener/wingman`, or `/review-setup` — compares the installed version against the version shipped in the pack:

- **older installed** → strips the old block and appends the new one (in-place upgrade)
- **same version** → skips, leaves the hook untouched
- **`--force` / `--reinstall`** → unconditionally replaces the block (use this when you want to force a re-stamp without bumping the version, e.g. recovering from a hand-edited hook)

This means bug fixes to the hook propagate automatically the next time you re-run setup. Pre-v2 installs (no version stamp) are treated as v1 and upgraded. v2 installs are upgraded to v3 in place.

#### What's new in v3

Four upgrades, all driven by lessons from a 12-round wingman convergence on `project-arc` spec 004 — see [`docs/wingman-v3-features.md`](docs/wingman-v3-features.md) for the full write-up.

| # | Feature | Effect |
|---|---|---|
| 1 | `.wingman-exemptions.yaml` | Codex skips findings ratified out-of-scope by the project (e.g. constitutional rules, ratified ADRs). The installer ships a sample at `.wingman-exemptions.yaml.sample`. |
| 2 | CI status awareness | After the review, the hook calls `gh pr checks` and prepends a synthetic P1 finding if a required check is RED — so the next remediation round addresses CI red instead of bandaging local-green code. |
| 3 | Round tracking + convergence detection | `.reviews/_convergence.json` ledger; emits `[CONVERGENCE NOTICE]` when the stop-rule fires (`0 P1 + ≤2 P2` for 2 consecutive rounds) and `[STAGNATION ALERT]` when the same finding ID flags twice in a row. |
| 4 | Audit-related-paths prompt | Codex now audits code paths importing from / imported by the changed modules — bigger per-round prompts → fewer total rounds. |

Run `bash scripts/install.sh --help` for full installer usage details.

## Configuration

The pre-push hook honors two optional environment variables. Both have sensible defaults.

| Var | Default | Effect |
|---|---|---|
| `WINGMAN_REVIEWER` | `codex` | Which reviewer CLI runs: `codex`, `gemini`, or `claude`. Pick a **different model than the one that wrote the code** — that's where cross-model value comes from. Resolution: this env var → a `.wingman-reviewer` repo file → `codex`. A missing/unknown reviewer CLI writes a `reviewer_missing` record instead of blocking the push. (Choosing `claude` in a Claude-authored repo still runs, with a note suggesting a different model.) |
| `WINGMAN_BASE` | `main` | Git base used for the review diff. Set to a feature-branch fix-commit SHA to review only the round-N delta — much faster than re-reviewing the whole branch each round. |
| `WINGMAN_MODEL` | _(unset)_ — the reviewer CLI's own latest | Pin a specific model for the selected reviewer (e.g. `gpt-5.5`). Leave unset for always-latest behavior; each reviewer CLI picks whichever model it supports. |

Examples:

```bash
# Faster iteration during a review-fix loop: review only the latest commit
WINGMAN_BASE=$(git rev-parse HEAD~1) git push

# Cost-tier control: pin to a smaller model
WINGMAN_MODEL=gpt-5.4 git push
```

### Pre-push sync reviews

The hook is always async — push proceeds immediately. When you want a sync review on a material change (the agent workflow), run codex manually before push:

```bash
codex review --base HEAD~1     # block ~60-90s; findings stream to terminal
# fix findings, repeat until clean
git push                       # hook fires async behind you (redundant but harmless)
```

This keeps the hook simple and lets sync vs async be an act-by-act choice rather than a global config knob.

## Output schema (`wingman_schema_version: "3"`)

`.reviews/<timestamp>-<branch>.json` looks like:

```jsonc
{
  "wingman_schema_version": "3",
  "branch": "feature-x",
  "timestamp": "2026-04-27-104051",
  "base": "main",
  "reviewer": {
    "tool": "codex",
    "tool_version": "0.121.0",
    "model": "gpt-5.5",
    "provider": "openai",
    "reasoning_effort": "medium",
    "session_id": "019dce11-...",
    "wall_seconds": 87
  },
  "ci_status": {                            // v3 — gh pr checks snapshot
    "state": "FAILURE",
    "checks": [/* …gh pr checks output… */],
    "pr_number": "42",
    "failing": [{ "name": "quality-gate", "state": "FAILURE", "link": "…" }]
  },
  "convergence": {                          // v3 — round summary
    "round": 8,
    "p1_count": 0,
    "p2_count": 2,
    "p3_count": 0,
    "stop_rule_met": true,
    "consecutive_zero_p1_rounds": 5,
    "stagnation_ids": [],
    "trend": "converging"
  },
  "exemptions": ["shim-files-flat-paths"],   // v3 — IDs from .wingman-exemptions.yaml
  "synthetic_findings": ["[P1] CI status: …"],
  "notices": ["[CONVERGENCE NOTICE] …"],
  "raw_review": "...full codex output...",
  "findings": [],
  "resolutions": [],
  "status": "needs_categorization"
}
```

The structured `reviewer` block makes it trivial to compare findings across models, plot review-time trends, and audit which model produced which output. v3 adds `ci_status`, `convergence`, `exemptions`, `synthetic_findings`, and `notices` — see [`docs/wingman-v3-features.md`](docs/wingman-v3-features.md). Older v1/v2 files (no `wingman_schema_version` or `"2"`) can be upgraded in place with `python3 scripts/migrate-reviews.py` from this repo.

## How it works

```
commit (x many)
  → pre-commit: linter (ruff/eslint) + fast checks [blocking]

push
  → pre-push: tests [blocking] + cross-model review [background, non-blocking]
  → push proceeds, you keep working
                                    ↓
                        findings saved to .reviews/
                                    ↓
        agent auto-surfaces the findings table in chat after push
        (no need to type /review-loop manually — it's ambient)
                                    ↓
              user chooses: all | agreed | one | defer | per-row | none
                     ↓
          "all"     → background agent fixes everything
          "agreed"  → background agent fixes only agent-approved findings
          "one"     → walk through 1-by-1 with diff preview (y/n/all/stop)
          "defer"   → record rationale + encode as known false positive
          "per-row" → e.g. `01:fix 02:defer 03:fix`
          "none"    → skip fixes, encode patterns only
                     ↓
              lint findings                   non-lint findings
                     ↓                              ↓
          add linter rule                  fix in code + encode
          (ruff, eslint, etc.)             in .claude/rules/review-patterns.md
                     ↓                              ↓
              auto-fix applied             pattern learned — won't recur
```

### The review table

A different model reviews your code. Your agent gives a second opinion. You make the call.

| # | Severity | Category | File | Opinion |
|---|---|---|---|---|
| 1/16 | 🔴 CRITICAL | security | `hello_world.py:114` | Agree — eval() is never safe |
| 2/16 | 🟠 HIGH | security | `hello_world.py:22` | Agree — classic SQL injection |
| 3/16 | 🟡 MEDIUM | logic | `hello_world.py:27` | Agree — null check needed |
| ... | ... | ... | ... | ... |

> **all** fix everything · **agreed** fix agent-approved · **one** walk through · **defer** record rationale · **per-row** e.g. `01:fix 02:defer` · **none** done

### The 1-by-1 walk-through

Each finding shows a diff preview. You respond `y`, `n`, `all`, or `stop`.

| # | Severity | Category | File | Opinion |
|---|---|---|---|---|
| 1/16 | 🔴 CRITICAL | security | `hello_world.py:114` | Agree |

```diff
- result = eval(user_input)
+ try:
+     result = int(user_input)
+ except ValueError:
+     print("Invalid input"); sys.exit(1)
```

> **y** fix · **n** skip · **all** fix remaining · **stop** done

## How it improves over time

```
Week 1:  Reviewer flags ~15 issues per review
         → 8 become linter rules, 5 become learned patterns

Week 2:  Reviewer flags ~7 issues
         → Agent already avoids the encoded patterns

Week 4:  Reviewer flags 2-3 issues
         → Mostly novel edge cases

Week 8:  Reviews are near-empty
         → /review-retro confirms — consider spot-checks only
```

## What gets created in your project

```
your-project/
├── .claude/rules/review-patterns.md   # Learned patterns (auto-loaded by agent)
├── .reviews/                          # Review data (gitignored)
│   ├── 2026-04-15-120000-feature-auth.json
│   ├── _convergence.json              # v3 — round-tracking ledger (gitignored)
│   └── ...
├── .wingman-exemptions.yaml.sample    # v3 — copy to .wingman-exemptions.yaml to activate
└── .git-hooks/pre-push                # Wingman block appended (or wherever your hooks live)
```

## Stack-agnostic

Wingman detects your project's linter automatically:
- Python → ruff
- JavaScript/TypeScript → eslint or biome
- Go, Rust, etc. → language-appropriate tooling

## CI

Every pull request runs [`.github/workflows/wingman-ci.yml`](.github/workflows/wingman-ci.yml), which exercises three jobs:

| Job | What it does |
|---|---|
| `lint` | `shellcheck --severity=error` on `scripts/install.sh` and `assets/pre-push.sample` |
| `syntax` | `bash -n` on both shell files; extracts the embedded Python heredoc from the hook and runs `py_compile` on it |
| `install-smoke` | Runs the installer through six scenarios — fresh install, v1 → v3 upgrade, v2 → v3 upgrade, `--force` reinstall, exemption-file parsing, and `_convergence.json` ledger schema validation — asserting the hook ends up with exactly one Wingman block and the correct `# wingman-hook-version` stamp |

CI runs on Linux. The installer itself is portable to macOS — PR #6 switched to a cross-platform `mktemp` invocation that works on both BSD (macOS) and GNU (Linux) coreutils, so the same `bash scripts/install.sh` flow is exercised in development on macOS and in CI on Linux.

## License

MIT
