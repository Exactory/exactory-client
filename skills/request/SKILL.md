---
description: Submit a paper to exactory for verification, check a verification's status, or read its result. Use when the user wants a paper verified, names exactory, or asks what came back for a submitted paper.
---

# Request a verification

The `exactory` command is on PATH while this plugin is enabled. It prints JSON on
success. It prints an error message on stderr and exits non-zero on failure.

If `EXACTORY_API_KEY` is not set, stop and tell the user: create an API key at
https://www.exactory.ai/console, then export it as `EXACTORY_API_KEY`. Do not ask the
user to paste the key into the chat.

## Submit a paper

1. Get the arXiv id or the arXiv DOI from the user. exactory verifies arXiv papers only.
2. Run `exactory submit --arxiv-id <id>` (or `--doi <doi>`).
3. Report the `id`, `status`, and `webUrl` fields to the user.

A repeat submit of the same paper returns the open request instead of a new one. Tell
the user when this occurred (the HTTP layer returns it without an error).

## Check a verification

1. Run `exactory status <verification-id>`.
2. Report the status. When claims are present, summarize per claim: `claimType`,
   `status`, `verdict`.
3. `paper` is null until ingest resolves the identifier against arXiv. Tell the user to
   check again later when it is null.

## Notes

- The requester's identity is never shown to verifiers, and verifier output reaches the
  requester through this status call.
- Do not poll in a loop. Check once, report, and let the user decide when to check again.
