# Cursor Token Tracker

[English](README.md)

每個 agent 回合結束後，記錄這一回的 token，以及這個對話依模型分開的累計。下一則回應會把兩張 markdown 表格接在正文最後。不會把文字打進對話輸入框。

數字來自回合結束時的 `stop` hook（`input_tokens`、`output_tokens`、`cache_read_tokens`、`cache_write_tokens`、`model`）。`input_tokens` 已含兩種快取。未快取輸入是 `input_tokens - cache_read_tokens - cache_write_tokens`，小於 0 就當 0。本回合合計是 `input_tokens + output_tokens`。

回應底下的表格是已經結束的回合。這一則自己的 token 要等回應寫完才知道。每一回只記一個模型。子代理的 token 不在這份資料裡。若沒有 token 欄位，這一回顯示「無 token 資料」，也不把 0 加進累計。

## 畫面上會看到

預設是繁體中文。若要英文：

```bash
mkdir -p ~/.cursor/cursor-token-tracker
printf 'en\n' > ~/.cursor/cursor-token-tracker/lang
```

第一張表是最近一次已結束的回合，表頭為：未快取輸入、快取讀取、快取寫入、輸出、合計。

第二張表是本對話累計：模型、同樣的用量、回合。每個模型一列，最後一列是「全部」。累計只算目前這個對話。

## 顯示範例

本回合 #2 · grok-4.7-high

| 未快取輸入 | 快取讀取 | 快取寫入 | 輸出 | 合計 |
| ---: | ---: | ---: | ---: | ---: |
| 36,335 | 941,440 | 0 | 25,334 | 1,003,109 |

本對話累計

| 模型 | 未快取 | 快取讀 | 快取寫 | 輸出 | 合計 | 回合 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| grok-4.7-high | 92,309 | 1,951,104 | 0 | 55,868 | 2,099,281 | 2 |
| 全部 | 92,309 | 1,951,104 | 0 | 55,868 | 2,099,281 | 2 |

## 需要

- 支援專案或使用者 hook 的 Cursor
- `/usr/bin/python3`

## 只在這個專案使用

複製 repo，用 Cursor 打開該資料夾。`.cursor/hooks.json` 會自己載入。

```bash
git clone https://github.com/louxmao/Cursor_Token_Tracker.git
cd Cursor_Token_Tracker
/usr/bin/python3 .cursor/hooks/token-tracker.py --selftest
```

印出 `ok` 表示腳本能記下一回合並排出表格。

## 每個專案都使用

把下面兩個項目合併進 `~/.cursor/hooks.json`。若檔案裡已經有別的 hook，把指令加在旁邊，不要整份覆蓋。

```json
{
  "version": 1,
  "hooks": {
    "beforeSubmitPrompt": [
      {
        "command": "/usr/bin/python3 /絕對路徑/Cursor_Token_Tracker/.cursor/hooks/token-tracker.py",
        "timeout": 10
      }
    ],
    "stop": [
      {
        "command": "/usr/bin/python3 /絕對路徑/Cursor_Token_Tracker/.cursor/hooks/token-tracker.py",
        "timeout": 10,
        "loop_limit": 1
      }
    ]
  }
}
```

把 `/絕對路徑` 換成 clone 下來的位置。Cursor 會在 `hooks.json` 存檔後重新載入。之後再送一則訊息，下一則回應的最後應出現表格。

已記錄的回合存在 `~/.cursor/cursor-token-tracker/state.json`。
