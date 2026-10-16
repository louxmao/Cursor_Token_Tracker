# Cursor Token Tracker

[繁體中文](README.zh-TW.md)

After each agent turn, record that turn's token use and the conversation total, split by model.

Cursor reports the numbers on the `stop` hook when the turn finishes (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `model`). `input_tokens` already includes both cache fields. Uncached input is `input_tokens - cache_read_tokens - cache_write_tokens`, clamped at zero. The turn total is `input_tokens + output_tokens`.

The hook writes an HTML page. It does not type into the chat input and it does not send another message. One model is stored per turn. Subagent tokens are not included. If the token fields are missing, that turn says `no token data` and adds nothing to the total.

## What you see

Open `~/.cursor/cursor-token-tracker/ledger.html` in a browser. The page reloads itself. Default language is Traditional Chinese. Write `en` into `~/.cursor/cursor-token-tracker/lang` for English.

This turn is one row under column headers: uncached input, cache read, cache write, output, total.

The conversation total is a second table: model, those same columns, and turns. One row per model, then `all models`. Totals stay inside the current conversation.

## Install

Opening this repository loads the project hook (`.cursor/hooks.json`) and the project skill.

To use it in every project, point a user `stop` hook at the script and link the skill:

```bash
# ~/.cursor/hooks.json  (merge into the existing file; do not replace other hooks)
# "stop": [{ "command": "/usr/bin/python3 /absolute/path/.cursor/hooks/token-tracker.py", "timeout": 10, "loop_limit": 1 }]

ln -sfn /absolute/path/Cursor_Token_Tracker/.cursor/skills/cursor-token-tracker \
  ~/.cursor/skills/cursor-token-tracker
```

Cursor reloads `hooks.json` on save. State is `~/.cursor/cursor-token-tracker/state.json`.

```bash
/usr/bin/python3 .cursor/hooks/token-tracker.py --selftest
```
