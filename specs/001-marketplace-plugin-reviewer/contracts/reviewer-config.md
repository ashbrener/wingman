# Contract: Reviewer configuration & output

## `WINGMAN_REVIEWER` (env var)

- **Values**: `codex` (default) | `gemini` | `claude`. Unrecognized → treated as unavailable.
- **Resolution precedence**: `WINGMAN_REVIEWER` env var → `.wingman-reviewer` repo file → `codex`.

## `WINGMAN_MODEL` (env var, optional)

- Pins a model for the *selected* reviewer. Unset → the reviewer CLI's own default/latest model.

## `.wingman-reviewer` (repo file)

- Single token: the reviewer name. Written by `/wingman:review-setup`. Read (never sourced) by the hook.

## Reviewer invocation contract

| Reviewer | Invocation | Diff source |
|---|---|---|
| codex | `codex review --base <base> [--prompt-file <f>]` (native) | codex computes it |
| gemini | constructed prompt piped via **stdin** | `git diff <base>...HEAD` |
| claude | `claude -p` with constructed prompt via **stdin** | `git diff <base>...HEAD` |

Constructed prompt (gemini/claude) = uniform preamble + existing audit/exemptions prompt + the three-dot diff. Input MUST go via stdin/prompt-file, never argv (ARG_MAX).

## Uniform finding-output contract (what reviewers are asked to emit)

```
[P1|P2|P3] <file>:<line> (<category>) — <one-line description>
```
- `category` ∈ {logic, security, architecture, lint}. `[P1]` critical, `[P2]` should-fix, `[P3]` nit.
- No findings → the single line `No findings.`
- The existing parser consumes this for all reviewers (no per-reviewer parsing).

## Failure / edge behavior

- **Reviewer CLI missing / unrecognized**: write a review record with `status: "reviewer_missing"` and an install/switch hint. **Push is never blocked** (runs backgrounded, `|| true`).
- **Reviewer = claude**: append non-blocking notice `[CROSS-MODEL NOTE] reviewer 'claude' may match the code author — for a true second opinion use codex or gemini`.
