# Contract: In-place hook upgrade (v1/v2/v3 → v4)

## Invariants

- The hook block's first line (marker) is byte-identical across versions:
  `# --- Wingman: Codex review (non-blocking) ---`
- The block carries `# wingman-hook-version: N`; v4 sets `N = 4`.
- `install.sh` derives the shipped version from the sample's stamp and compares
  it to the installed stamp (absent stamp ⇒ v1).

## Behavior

| Installed | Action | Result |
|---|---|---|
| none | append/create | one block, v4 |
| v1 / v2 / v3 | strip old block, append new | exactly one block, v4 |
| v4 | skip (unless `--force`) | unchanged |
| `--force` | strip + replace regardless | exactly one block, v4 |

- Upgrades MUST preserve `.reviews/*.json` and `.reviews/_convergence.json`.
- After any path there is **exactly one** Wingman block (asserted by CI
  `count_blocks` = 1).
