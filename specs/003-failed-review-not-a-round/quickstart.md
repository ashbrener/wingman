# Quickstart — verifying the fix

## Replay the sequences

```bash
python3 scripts/verify-convergence.py
```

It runs the hook's payload writer, extracted from `assets/pre-push.sample`,
through these push sequences in a scratch directory:

| Sequence | Expectation |
|---|---|
| missing → missing | 0 rounds, 2 uncounted runs, stop-rule never met, no convergence notice, status `reviewer_missing` |
| codex 401 (exit 1) → codex 401 (exit 1) | 0 rounds, 2 uncounted runs, stop-rule never met, status `review_failed`, raw output kept |
| codex 401 with exit 0 | still `failed` — the error signature ends a findings-free output |
| clean → codex 401 → clean | 2 rounds, 1 uncounted run, stop-rule met on round 2 |
| findings → failed → clean | streak and trend compare the two real rounds |
| clean → clean | stop-rule met on round 2, as before |
| findings with error-like text, exit 0 | `succeeded` — findings are never discarded |
| empty output, exit 0 | `failed` |

`python3 scripts/verify-parser.py` must still pass unchanged.

## On a real repo

1. Re-run `/review-setup` (marker 5 → 6 replaces the block).
2. `codex logout`, then push a feature branch twice.
3. Read `.reviews/_convergence.json`: no new rounds, two `uncounted_runs`, and
   the artifacts carry `status: "review_failed"` with the 401 in `raw_review`.
4. `codex login`, push again: that review is the next real round.
