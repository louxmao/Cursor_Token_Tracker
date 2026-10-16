# Cursor Token Tracker

[繁體中文](README.zh-TW.md)

After each agent turn, record that turn's token use and the conversation total, split by model.

Cursor reports the numbers on the `stop` hook when the turn finishes (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `model`). `input_tokens` already includes both cache fields. Uncached input is `input_tokens - cache_read_tokens - cache_write_tokens`, clamped at zero. The turn total is `input_tokens + output_tokens`.

The hook does not type into the chat input and does not send another message. On the next prompt it gives the model the finished turns, and the model pastes two markdown tables at the end of that reply. The numbers under a reply are the turns already finished, because this reply's own tokens are only known after the reply is done. One model is stored per turn. Subagent tokens are not included. If the token fields are missing, that turn says `no token data` and adds nothing to the total.

## What you see

Default language is Traditional Chinese. Write `en` into `~/.cursor/cursor-token-tracker/lang` for English.

The first table is the last finished turn: uncached input, cache read, cache write, output, total.

The second table is the conversation total: model, the same measures, and turns. One row per model, then `all models`. Totals stay inside the current conversation.

## Install

Opening this repository loads the project hook (`.cursor/hooks.json`) and the project skill.

To use it in every project, point a user `stop` hook at the script and link the skill:

```bash
# ~/.cursor/hooks.json  (merge into the existing file; do not replace other hooks)
# "beforeSubmitPrompt": [{ "command": "/usr/bin/python3 /absolute/path/.cursor/hooks/token-tracker.py", "timeout": 10 }]
# "stop": [{ "command": "/usr/bin/python3 /absolute/path/.cursor/hooks/token-tracker.py", "timeout": 10, "loop_limit": 1 }]

ln -sfn /absolute/path/Cursor_Token_Tracker/.cursor/skills/cursor-token-tracker \
  ~/.cursor/skills/cursor-token-tracker
```

Cursor reloads `hooks.json` on save. State is `~/.cursor/cursor-token-tracker/state.json`.

```bash
/usr/bin/python3 .cursor/hooks/token-tracker.py --selftest
```
