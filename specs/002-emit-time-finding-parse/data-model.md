# Data model — emit-time findings

## Parsed finding (new)

One entry per finding the reviewer reported.

| Field | Type | Notes |
|---|---|---|
| `file` | string | as the reviewer wrote it (repo-relative in practice) |
| `line` | integer \| null | null when the reviewer stated no line |
| `category` | `lint` \| `logic` \| `architecture` \| `security` | closed vocabulary — part of the qualifying test |
| `severity` | `critical` \| `high` \| `medium` \| `low` | closed vocabulary — part of the qualifying test |
| `priority` | `P1` \| `P2` \| `P3` | derived: critical/high→P1, medium→P2, low→P3 |
| `description` | string | remainder of the line; may itself contain `\|` |

**Qualifying rule**: a line becomes a finding only when it matches
`file[:line] | category | severity | description` AND both vocabularies match.
Anything else is prose.

## Round summary (existing, now truthful)

| Field | Change |
|---|---|
| `p1_count` / `p2_count` / `p3_count` | now `max(native parse, legacy grep)`; synthetic CI-red findings still added to P1 |
| `stagnation_ids` | now also includes `file:line` identities from parsed findings |
| `stop_rule_met`, `consecutive_zero_p1_rounds`, `trend` | unchanged logic, true inputs |

## Review artifact (schema 4)

Unchanged fields: `branch`, `timestamp`, `base`, `reviewer`, `ci_status`,
`convergence`, `exemptions`, `synthetic_findings`, `notices`, `raw_review`,
`findings`, `resolutions`, `status`.

| Change | Detail |
|---|---|
| `wingman_schema_version` | `"3"` → `"4"` |
| `parsed_findings` | NEW array of parsed findings; `[]` is an honest "reviewer reported nothing" |
| `findings` | unchanged — still `[]` at emit; the review loop's categorization target |

**Migration 3 → 4**: add `parsed_findings: []`. Older artifacts remain readable;
an empty array on a v3-migrated file truthfully means "written before parsing
existed".

## States

- `clean` — nothing to review (unchanged).
- `needs_categorization` — the reviewer reported output; `parsed_findings` now
  says what, while `findings` stays empty until routed.
- `reviewer_missing` — unchanged; `parsed_findings` is `[]` and no finding is
  invented.
