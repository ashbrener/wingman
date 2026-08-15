# Contract — review artifact v4 and the parsing rule

## The parsed line

```
<file>[:<line>] | <category> | <severity> | <description>
```

- `category` ∈ `lint | logic | architecture | security`
- `severity` ∈ `critical | high | medium | low`
- matching is case-insensitive; surrounding whitespace is free
- the line number is optional; everything after the third pipe is the
  description and may contain further pipes
- **both vocabularies must match** — this is what makes prose containing pipes
  an honest zero

## The legacy line (still supported)

`[P1] …`, `P1: …`, `P1 - …`, `Priority 1 …` — the contract used by the
constructed gemini/claude prompts. Support for the native shape must never
reduce support for this one.

## Counting

```
p{n}_count = max( count of parsed findings with priority P{n},
                  legacy grep count for P{n} )
```

Synthetic CI-red findings continue to add to `p1_count`.

**Invariant**: with at least one finding present in either shape, no count is
zero — therefore `stop_rule_met` cannot be true and no convergence
recommendation can be emitted.

## Emission

- `parsed_findings`: the parsed list (possibly empty).
- `findings`: `[]` — reserved for `/review-loop` categorization.
- `wingman_schema_version`: `"4"`.
- Everything else unchanged, including the non-blocking, backgrounded run and
  the `reviewer_missing` path.

## Single-sourcing

The parser lives ONCE, inside `assets/pre-push.sample`, fenced by unique anchor
comments. `scripts/verify-parser.py` extracts it between those anchors (after
asserting each appears exactly once) and exercises it. No second copy exists.
