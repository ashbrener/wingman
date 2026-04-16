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
# 1. Install skills (for Claude Code, Cursor, and 40+ other agents)
npx skills add ashbrener/wingman

# 2. Install git hook + .reviews/ + rules file into your project
bash <(curl -s https://raw.githubusercontent.com/ashbrener/wingman/main/scripts/install.sh)
# or if you've cloned the repo:
./scripts/install.sh

# 3. Work on your feature branch, commit, push
#    Codex reviews in background after push — you keep working

# 4. Before opening a PR, process findings
/review-loop

# 5. Weekly, run a retrospective
/review-retro
```

The install script is idempotent — safe to run multiple times. It detects your hooks directory (`.git-hooks/`, `.githooks/`, `.husky/`, or `.git/hooks/`) and appends to existing pre-push hooks rather than overwriting.

## How it works

```
commit (x many)
  → pre-commit: linter (ruff/eslint) + fast checks [blocking]

push
  → pre-push: tests [blocking] + Codex review [background, non-blocking]
  → push proceeds, you keep working
                                    ↓
                        findings saved to .reviews/
                                    ↓
                    /review-loop presents numbered table
                                    ↓
              user chooses: fix all | critical only | one-by-one | skip
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
└── .git-hooks/pre-push                # Wingman block appended (or wherever your hooks live)
```

## Stack-agnostic

Wingman detects your project's linter automatically:
- Python → ruff
- JavaScript/TypeScript → eslint or biome
- Go, Rust, etc. → language-appropriate tooling

## License

MIT
