---
name: cursor-token-tracker
description: >-
  Echo the token ledger that the stop hook posts after each turn. Use when the
  user message starts with "Token ·" and is a per-turn token report.
---

# Token ledger echo

The stop hook submits the ledger as the next user message. When that message starts with `Token ·`:

- Reply with the same ledger text only. Do not wrap it in a code fence.
- Do not call tools, and do not add words before or after the ledger.

Do not invent token counts.
