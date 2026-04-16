# Wingman

Cross-model code review feedback loop that learns from every review and makes itself progressively unnecessary.

Wingman gets a second opinion on your code from a different AI model, then feeds findings back into your project's rules and linter config so the same mistakes never recur.

## Why cross-model?

The model that writes your code has blind spots — it follows its own patterns and won't catch its own mistakes. A different model reviews from first principles, catching things the first model would never flag on itself.

For example: if Claude Opus writes your code, use Codex (GPT) as the reviewer. If Gemini writes your code, use Claude as the reviewer. The point is **the reviewer is a different model than the writer** — that's where the value comes from.

Wingman ships with [Codex](https://github.com/openai/codex) as the default reviewer. `/review-setup` will install it for you if it's not already present.

## Install

```bash
npx skills add ashbrener/wingman
```

This installs three skills into your AI coding agent:

| Skill | Command | Purpose |
|---|---|---|
| `review-setup` | `/review-setup` | Install git hook, `.reviews/` dir, and patterns rule file |
| `review-loop` | `/review-loop` | Review → categorize → fix → encode learned patterns |
| `review-retro` | `/review-retro` | Weekly retrospective — trends, pruning, automation recs |

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

# 4. Before opening a PR, process findings
/review-loop

# 5. Weekly, run a retrospective
/review-retro
```

`/review-setup` is idempotent — safe to run multiple times. It detects your hooks directory (`.git-hooks/`, `.githooks/`, `.husky/`, or `.git/hooks/`) and appends to existing pre-push hooks rather than overwriting.

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
            /review-loop presents overview table with your agent's opinion
                                    ↓
              user chooses: all | agreed | one | none
                     ↓
          "all"     → background agent fixes everything
          "agreed"  → background agent fixes only agent-approved findings
          "one"     → walk through 1-by-1 with diff preview (y/n/all/stop)
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

> **all** fix everything · **agreed** fix agent-approved · **one** walk through · **none** done

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
