# Contract — review outcome and round counting (hook v6)

## Inputs to the payload writer

| Env var | Meaning |
|---|---|
| `WINGMAN_REVIEW_INPUT` | path to the reviewer's combined stdout+stderr (unchanged) |
| `WINGMAN_TOOL` | the reviewer: `codex`, `gemini`, `claude`, or an unknown name (unchanged) |
| `WINGMAN_REVIEWER_EXIT` | NEW — the reviewer CLI's exit status (the last attempt's, when codex retries without `--prompt-file`). Unset or empty when the CLI never ran. |

## Classification

```
missing    if raw starts with "WINGMAN_REVIEWER_MISSING"
failed     if WINGMAN_REVIEWER_EXIT is set and non-zero
failed     if raw is empty or whitespace
failed     if a signature for WINGMAN_TOOL matches a line among the last 5
           non-empty lines AND the run reported no findings in either shape
succeeded  otherwise
```

Signatures are line-anchored and case-insensitive; the per-reviewer lists live
in `_REVIEW_FAILURE_SIGNATURES` in the hook and in research R-3.

## Counting

- `succeeded` → appended to `rounds`; round number = `len(rounds)`; stop-rule,
  streak, stagnation and trend computed exactly as in v5.
- `failed` / `missing` → appended to `uncounted_runs`; `rounds` and the ledger's
  `convergence` summary untouched; the artifact reports `round: null`,
  `counted: false`, `stop_rule_met: false`.

**Invariant**: the stop-rule can only be met by two succeeded reviews. No
sequence of failed or missing runs can meet it, reset it, or advance it.

## Emission

- `review_outcome: {state, reason, exit_status, counted}` on every artifact.
- `status`: `reviewer_missing` | `review_failed` for uncounted runs; otherwise
  as before.
- The artifact is always written, never blocks the push.
