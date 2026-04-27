---
name: review-retro
description: Retrospective analysis of Wingman reviews — identify trends, prune stale patterns, and recommend automation improvements
---

# Wingman: Review Retro

Perform a retrospective analysis of accumulated review data. Identify what's working, what's not, and refine the feedback loop.

Run this weekly or when review findings feel repetitive.

## Step 1: Load review data

Read all `.json` files in `.reviews/` with `"status": "categorized"`.
Also read the current `.claude/rules/review-patterns.md`.

If fewer than 3 categorized reviews exist, tell the user there isn't enough data yet and suggest running more `/review:loop` cycles first.

### Schema-aware reading

Files written by wingman v2 (`wingman_schema_version: "2"`) carry a
top-level `reviewer` block with `tool_version`, `model`, `provider`,
`reasoning_effort`, `session_id`, and `wall_seconds`. Use these when
analysing trends:

- Group findings by `reviewer.model` to compare findings produced by
  different models (e.g. did gpt-5.5 surface different patterns than
  gpt-5.4?).
- Plot `reviewer.wall_seconds` over time to spot codex performance
  regressions or model-tier upgrades.
- Group by `reviewer.tool_version` when interpreting findings — a tool
  upgrade can change which categories surface.

Older v1 files (no `wingman_schema_version`) lack these fields. Either
run `python3 scripts/migrate-reviews.py` from the wingman repo to
backfill (best-effort extraction from `raw_review` prose), or treat
v1 files as `model: "unknown"` for trend analysis.

## Step 2: Frequency analysis

Identify the top 5 most frequent finding patterns across all reviews. For each:
- How many times has it appeared?
- Which category (lint / logic / architecture / security)?
- Is it already covered by a linter rule or a learned pattern in `.claude/rules/review-patterns.md`?
- If covered, is it still appearing? (This means the rule isn't clear enough or isn't being followed)

## Step 3: Rule effectiveness

For each pattern in `.claude/rules/review-patterns.md`:
- Has the pattern appeared in any review in the last 2 weeks?
- If yes → the rule needs to be clearer or more specific. Rewrite it.
- If no for 4+ weeks → the rule is working. Consider whether it's still needed or can be archived.
- If the pattern could be enforced by a linter rule instead, recommend the specific rule.

## Step 4: Automation opportunities

Look for findings categorized as "logic" that could be automated:
- Can it become a linter rule (ruff, eslint, biome)?
- Can it become a type checking rule (mypy strict mode, TypeScript strict)?
- Can it become a test pattern or fixture?
- Can it become a pre-commit check?

For each opportunity, explain specifically what rule or check to add.

## Step 5: Trend analysis

If there are reviews spanning more than 1 week, calculate:
- Average findings per review (first half vs second half of available data)
- Are findings decreasing over time? (the system is working)
- Are findings stable? (rules aren't being applied — investigate)
- Are findings increasing? (new patterns emerging — expected during active development)

## Step 6: Prune and update

Based on the analysis:
1. Remove stale patterns from `.claude/rules/review-patterns.md` (no appearances in 4+ weeks)
2. Rewrite unclear patterns that keep recurring despite being documented
3. Add any new automation rules identified in Step 4

Commit changes:
```
docs(review): retro — prune stale patterns, refine rules
```

## Step 7: Report

Print a structured report:

```
Wingman Retro Report
====================

Reviews analyzed: N (date range: YYYY-MM-DD to YYYY-MM-DD)

Trend: findings are [decreasing/stable/increasing]
  First half avg: X findings/review
  Second half avg: Y findings/review

Top recurring patterns:
  1. <pattern> — N occurrences — [covered/not covered]
  2. ...

Rule effectiveness:
  - Active and working: N patterns
  - Needs rewrite: N patterns
  - Stale (archived): N patterns

Automation recommendations:
  - <specific rule to add to linter/type checker>
  - ...

Actions taken:
  - Archived N stale patterns
  - Rewrote N unclear patterns
  - Added N new patterns
```
