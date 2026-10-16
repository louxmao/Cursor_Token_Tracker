---
name: cursor-token-tracker
description: >-
  Tell the user where the local token ledger page is. Use only when they ask
  for token usage. Do not paste counts into the chat input.
disable-model-invocation: true
---

# Token ledger

The stop hook writes `~/.cursor/cursor-token-tracker/ledger.html` after each turn. It is a table and it refreshes itself.

Do not invent token counts. Do not type the ledger into the composer or submit it as a user message.
