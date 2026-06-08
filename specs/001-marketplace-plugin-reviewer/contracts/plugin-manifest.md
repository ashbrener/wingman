# Contract: Plugin & marketplace manifests

## `.claude-plugin/plugin.json`

```json
{
  "$schema": "https://json.schemastore.org/claude-code-plugin-manifest.json",
  "name": "wingman",
  "displayName": "Wingman",
  "version": "1.0.0",
  "description": "Cross-model code review that deletes its own findings. A different AI model reviews your diff on push; accepted findings are encoded back into your project rules and linter config so the same mistake can't recur.",
  "author": { "name": "Ash Brener", "url": "https://github.com/ashbrener" },
  "homepage": "https://github.com/ashbrener/wingman",
  "repository": "https://github.com/ashbrener/wingman",
  "license": "MIT",
  "keywords": ["code-review", "cross-model", "review", "linting", "git-hook", "code-quality", "self-improving"]
}
```

- Only `name` is required. `keywords` MUST be an array. Unknown fields are warnings only; `--strict` must be clean.
- Skills auto-discovered from root `skills/` → `/wingman:review-setup`, `/wingman:review-loop`, `/wingman:review-retro`. No `skills` field needed.

## `.claude-plugin/marketplace.json`

```json
{
  "name": "wingman",
  "owner": { "name": "Ash Brener", "url": "https://github.com/ashbrener" },
  "plugins": [
    {
      "name": "wingman",
      "source": "./",
      "description": "Cross-model code review that learns from every review and makes itself progressively unnecessary."
    }
  ]
}
```

- `source: "./"` ⇒ the repo root is the plugin source.

## Validation contract

- `claude plugin validate . --strict` exits 0 with no errors and no unrecognized-field warnings.
