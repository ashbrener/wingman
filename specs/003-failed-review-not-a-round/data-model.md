# Data model — review outcome

## Review outcome (new, on every artifact from hook v6)

| Field | Type | Notes |
|---|---|---|
| `state` | `succeeded` \| `failed` \| `missing` | per the detection rule in research R-3 |
| `reason` | string \| null | null when succeeded; otherwise why, e.g. `reviewer exited with status 1` |
| `exit_status` | integer \| null | the reviewer CLI's exit status; null when it never ran or was not reported |
| `counted` | boolean | true only for `succeeded` — whether this run is a convergence round |

## Artifact changes (schema stays 4)

| Field | Change |
|---|---|
| `review_outcome` | NEW object, above |
| `status` | new value `review_failed`; `reviewer_missing` unchanged |
| `convergence.round` | `null` for an uncounted run |
| `convergence.counted` | NEW boolean, mirrors `review_outcome.counted` |
| `convergence.stop_rule_met` | always `false` for an uncounted run |
| `notices` | `[REVIEW FAILED]` / `[REVIEWER MISSING]` for an uncounted run; never a convergence notice |
| `raw_review`, `parsed_findings` | unchanged — the failed output is kept |

An artifact without `review_outcome` was written by hook v5 or older; its
outcome is unknown.

## Ledger (`_convergence.json`)

| Field | Change |
|---|---|
| `rounds` | succeeded reviews ONLY — unchanged shape |
| `uncounted_runs` | NEW list: `{timestamp, review_file, state, reason, exit_status}` |
| `convergence` | recomputed only when a round is recorded; an uncounted run leaves it exactly as it was |

Rounds in a ledger written by an older hook carry no outcome and are treated as
counted, as before.

## States

- `succeeded` → a round: numbered, counted toward stop-rule, streak, stagnation, trend.
- `failed` → reviewer ran and did not complete (non-zero exit, empty output, or
  an error signature ending a findings-free output). Uncounted.
- `missing` → reviewer CLI not on PATH, or an unknown reviewer name. Uncounted.
