# Cursor Token Tracker

[繁體中文](README.zh-TW.md)

After each agent turn, record that turn's token use and the conversation total, split by model.

Cursor reports the numbers on the `stop` hook when the turn finishes (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `model`). `input_tokens` already includes both cache fields. Uncached input is `input_tokens - cache_read_tokens - cache_write_tokens`, clamped at zero. The turn total is `input_tokens + output_tokens`.

The same hook is the only way to place text after the answer, so the ledger is submitted as the next user message. A skill tells the agent to echo that ledger and stop. The echo turn (`loop_count > 0`) is not added to the totals. One model is stored per turn. Subagent tokens are not included. If the token fields are missing, the turn says `no token data` and adds nothing to the total.

## What you see

Default language is Traditional Chinese. Write `en` into `~/.cursor/cursor-token-tracker/lang` for English.

```
Token · turn #4 · grok-4.7
  uncached input      1,204
  cache read        842,110
  cache write        18,440
  output              3,902
  turn total        865,656

conversation total
  grok-4.7      uncached 12,400 · cache read 2,100,000 · cache write 40,000 · output 18,200 · total 2,170,600
  composer-2.5  uncached 3,100 · cache read 0 · cache write 8,200 · output 1,450 · total 12,750
  all models    uncached 15,500 · cache read 2,100,000 · cache write 48,200 · output 19,650 · total 2,183,350 · 4 turns
```

Totals stay inside the current conversation.

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
