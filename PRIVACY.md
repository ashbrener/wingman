# Wingman Privacy Policy

_Last updated: 2026-06-08_

Wingman is a **local developer tool** — a git `pre-push` hook plus Claude Code
skills. It runs entirely on your own machine and within your own version-control
workflow.

## What Wingman collects

**Nothing.** Wingman has no servers, no telemetry, no analytics, and sends no
data to its authors or to any third party of its own.

## Data Wingman creates on your machine

- Review records under `.reviews/` (JSON) and a convergence ledger at
  `.reviews/_convergence.json`. These stay inside your repository (gitignored by
  default).
- Learned patterns in `.claude/rules/review-patterns.md`, plus any rules added to
  your linter config. These become part of your project.

You own and control these files. Deleting them removes the data.

## Data sent to third parties (by tools you configure)

Wingman asks a **reviewer CLI that you choose** — `codex` (OpenAI), `gemini`
(Google), or `claude` (Anthropic) — to review your code. When a review runs, your
diff and related code context are sent to that provider **through that provider's
own CLI, authenticated with your own account**, and are governed by that
provider's privacy policy and terms:

- OpenAI / Codex — https://openai.com/policies/privacy-policy
- Google / Gemini — https://policies.google.com/privacy
- Anthropic / Claude — https://www.anthropic.com/legal/privacy

Wingman does not transmit this data itself and never receives a copy. If your
code is sensitive, choose a reviewer whose terms meet your requirements, scope
the review with `WINGMAN_BASE`, or do not run the review.

Optionally, when the GitHub CLI (`gh`) is installed, Wingman reads your pull
request's CI status from GitHub using your own `gh` authentication. No CI data
leaves GitHub beyond what your existing GitHub configuration already allows.

## Contact

Questions or concerns: please open an issue at
https://github.com/ashbrener/wingman/issues

## Changes

This policy may be updated over time; the _Last updated_ date above reflects the
current version.
