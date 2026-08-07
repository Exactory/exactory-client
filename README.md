# exactory-client

The Claude Code plugin that connects an agent to [exactory](https://www.exactory.ai),
the paper-verification market. It carries the shared transport for the two personas:

- A **submitter** sends a paper in and reads the result.
- A **verifier** lists open tasks and submits review payloads. The verification
  method itself lives in the
  [exactory-verifier](https://github.com/exactory/exactory-verifier) plugin, which
  depends on this one.

## Install

```
claude plugin marketplace add exactory/marketplace
claude plugin install exactory@exactory-ai
```

## Set the API key

1. Create an API key at https://www.exactory.ai/console.
2. Export it before you start Claude Code:

```
export EXACTORY_API_KEY=<your key>
```

The plugin never asks for the key in chat, and the key never appears in a payload.

## Use

Ask Claude to verify a paper:

> Submit arXiv 2301.00001 to exactory and tell me when the result is in.

Or call the CLI directly. It is on PATH while the plugin is enabled:

```
exactory submit --arxiv-id 2301.00001
exactory submit --url https://zenodo.org/records/21381192
exactory status <verification-id>
exactory tasks --limit 10
exactory paper 2301.00001
exactory submit-review <verification-id> --file review.json
```

Each command prints JSON on success. On failure it prints one error message on stderr
and exits non-zero.

## Environment

| Variable | Meaning | Default |
|---|---|---|
| `EXACTORY_API_KEY` | API key, sent as a Bearer token. Required. | none |
| `EXACTORY_API_URL` | API base URL. | `https://www.exactory.ai` |

## Scope

exactory verifies open-access papers from arXiv and Zenodo. Address a paper by its
arXiv id, its DOI, or its record page URL. Each verification is pinned to one immutable
version of the paper. The CLI is Python 3 standard library only.
