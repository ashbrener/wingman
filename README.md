# Wingman

Your AI review copilot. Cross-model code review feedback loop that learns from every review and makes itself progressively unnecessary.

Wingman uses [OpenAI Codex](https://github.com/openai/codex) as a second-opinion reviewer inside [Claude Code](https://claude.ai/code), then feeds findings back into your project's rules and linter config so the same mistakes never recur.

## Install

```bash
npx skills add starlogik/wingman
```

This installs three skills into your Claude Code (and any other supported agent):

| Skill | Command | Purpose |
|---|---|---|
| `review-setup` | `/review-setup` | Install git hook, `.reviews/` dir, and patterns rule file |
| `review-loop` | `/review-loop` | Review → categorize → fix → encode learned patterns |
| `review-retro` | `/review-retro` | Weekly retrospective — trends, pruning, automation recs |

## Prerequisites

- [Codex CLI](https://github.com/openai/codex) installed and authenticated
- [codex-plugin-cc](https://github.com/openai/codex-plugin-cc) installed in Claude Code
- A git repository

## Quick start

```bash
# 1. Install Wingman
npx skills add starlogik/wingman

# 2. In Claude Code, set up your project
/review-setup

# 3. After completing a task, run the review loop
/review-loop

# 4. Weekly, run a retrospective
/review-retro
```

## How it works

```
commit → post-commit hook runs Codex review in background
                                    ↓
                        findings saved to .reviews/
                                    ↓
            /review-loop categorizes: lint | logic | architecture | security
                     ↓                              ↓
              lint findings                   non-lint findings
                     ↓                              ↓
          add linter rule                  fix in code + encode
          (ruff, eslint, etc.)             in .claude/rules/review-patterns.md
                     ↓                              ↓
              auto-fix applied             pattern learned — won't recur
```

## How it improves over time

```
Week 1:  Codex flags ~15 issues per review
         → 8 become linter rules, 5 become learned patterns

Week 2:  Codex flags ~7 issues
         → Agent already avoids the encoded patterns

Week 4:  Codex flags 2-3 issues
         → Mostly novel edge cases

Week 8:  Reviews are near-empty
         → /review-retro confirms — consider spot-checks only
```

## What gets created in your project

```
your-project/
├── .claude/rules/review-patterns.md   # Learned patterns (auto-loaded by Claude Code)
├── .reviews/                          # Review data (gitignored)
│   ├── 2026-04-15-120000-feature-auth.json
│   └── ...
└── .git-hooks/post-commit             # (or wherever your hooks live)
```

## Stack-agnostic

Wingman detects your project's linter automatically:
- Python → ruff
- JavaScript/TypeScript → eslint or biome
- Go, Rust, etc. → language-appropriate tooling

## License

MIT
