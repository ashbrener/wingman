# Quickstart: Wingman

## Install (Claude Code plugin — recommended)

```bash
/plugin marketplace add ashbrener/wingman
/plugin install wingman
/wingman:review-setup           # pick a reviewer; wires the hook + .reviews/ + rules
```

## Install (any agent — skills CLI)

```bash
npx skills add ashbrener/wingman
/review-setup
```

## Pick your reviewer

Wingman defaults to **codex**. Choose a *different model than the one that wrote
your code* for a true second opinion.

```bash
# Per-push override:
WINGMAN_REVIEWER=gemini git push

# Or persist a repo default (review-setup does this for you):
echo gemini > .wingman-reviewer
```

Supported: `codex` (default), `gemini`, `claude`. (Choosing `claude` while Claude
wrote the code still works, but Wingman notes that a different model gives a
genuine cross-model opinion.)

## Use it

1. Work on a feature branch, commit, push.
2. The review runs in the background — your push is never blocked. If the chosen
   reviewer isn't installed, the push still succeeds and the review record says so.
3. The findings table surfaces in chat ~60–120s later. Choose:
   `all` · `agreed` · `one` · `defer` · `per-row` · `none`.
4. Accepted findings are fixed **and encoded** into `.claude/rules/review-patterns.md`
   + your linter config, so the same issue can't recur.
5. Weekly: `/wingman:review-retro` for trends + pruning.

## Verify it's working

```bash
ls .reviews/                    # review records appear here after a push
cat .reviews/_convergence.json  # round/convergence ledger
```
