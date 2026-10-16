# Cursor Token Tracker

[繁體中文](README.zh-TW.md)

After each agent turn, record that turn's token use and the running total for the conversation, split by model. The next reply pastes two markdown tables at the end. Nothing is typed into the chat input.

Cursor reports the numbers on the `stop` hook (`input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_write_tokens`, `model`). `input_tokens` already includes both cache fields. Uncached input is `input_tokens - cache_read_tokens - cache_write_tokens`, clamped at zero. The turn total is `input_tokens + output_tokens`.

The tables under a reply are turns that have already finished. This reply's own tokens are known only after it is written. One model is stored per turn. Subagent tokens are not included. A turn with no token fields says `no token data` and adds nothing to the total.

## What you see

Default language is Traditional Chinese. For English, run:

```bash
mkdir -p ~/.cursor/cursor-token-tracker
printf 'en\n' > ~/.cursor/cursor-token-tracker/lang
```

The first table is the last finished turn: uncached input, cache read, cache write, output, total.

The second table is the conversation total: model, those same measures, and turns. One row per model, then `all models`. Totals stay inside the current conversation.

## Example

Turn #2 · grok-4.7-high

| uncached input | cache read | cache write | output | total |
| ---: | ---: | ---: | ---: | ---: |
| 36,335 | 941,440 | 0 | 25,334 | 1,003,109 |

conversation total

| model | uncached | cache read | cache write | output | total | turns |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| grok-4.7-high | 92,309 | 1,951,104 | 0 | 55,868 | 2,099,281 | 2 |
| all models | 92,309 | 1,951,104 | 0 | 55,868 | 2,099,281 | 2 |

## Requirements

- Cursor with project or user hooks
- `/usr/bin/python3`

## Install for this project

Clone the repo and open that folder in Cursor. `.cursor/hooks.json` loads by itself.

```bash
git clone https://github.com/louxmao/Cursor_Token_Tracker.git
cd Cursor_Token_Tracker
/usr/bin/python3 .cursor/hooks/token-tracker.py --selftest
```

`ok` means the script can record a turn and format the tables.

## Install for every project

Merge these two entries into `~/.cursor/hooks.json`. If that file already has hooks, add the commands beside them. Do not replace the file.

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      {
        "command": "/usr/bin/python3 /ABSOLUTE/PATH/Cursor_Token_Tracker/.cursor/hooks/token-tracker.py",
        "timeout": 10
      }
    ],
    "stop": [
      {
        "command": "/usr/bin/python3 /ABSOLUTE/PATH/Cursor_Token_Tracker/.cursor/hooks/token-tracker.py",
        "timeout": 10,
        "loop_limit": 1
      }
    ]
  }
}
```

Replace `/ABSOLUTE/PATH` with the clone location. Cursor reloads `hooks.json` on save. Send one message after that. The following reply should end with the tables.

Recorded turns are stored in `~/.cursor/cursor-token-tracker/state.json`.
