# Quickstart — verifying the fix

## Replay the incident (the acceptance moment)

```bash
python3 scripts/verify-parser.py
```

Expected: the recorded codex review (`tests/fixtures/incident-native.txt`)
yields **3 findings — 2 × P1, 1 × P2**, where the previous version yielded 0 and
reported `stop_rule_met: true`.

## The four fixtures

| Fixture | Expectation |
|---|---|
| `incident-native.txt` | 3 findings (2 high → P1, 1 medium → P2) |
| `legacy-priority.txt` | legacy shape still counted (native parse 0, legacy grep non-zero) |
| `no-findings.txt` | 0 findings, honest zero |
| `prose-with-pipes.txt` | 0 findings — no false positives |

## On a real repo

1. Re-run `/review-setup` in a repo with the old hook (marker 4 → 5 triggers the
   replacement).
2. Push a branch with a real defect.
3. Read `.reviews/<stamp>-<branch>.json`: `parsed_findings` is populated,
   `convergence.p1_count` is non-zero, `stop_rule_met` is false, and no
   "declare convergence" notice appears.
4. Confirm the push was never blocked and `findings` is still `[]` — the review
   loop still owns categorization.
