# Cursor Token Tracker

[English](README.md)

每個 agent 回合結束後，記錄這一回的 token，以及這個對話依模型分開的累計。

數字來自回合結束時的 `stop` hook（`input_tokens`、`output_tokens`、`cache_read_tokens`、`cache_write_tokens`、`model`）。`input_tokens` 已含兩種快取。未快取輸入是 `input_tokens - cache_read_tokens - cache_write_tokens`，小於 0 就當 0。本回合合計是 `input_tokens + output_tokens`。

Hook 會寫一個 HTML 頁面。它不會把文字打進對話輸入框，也不會再送出一則訊息。每一回只記一個模型。子代理的 token 不在這份資料裡。若沒有 token 欄位，這一回顯示「無 token 資料」，也不把 0 加進累計。

## 畫面上會看到

用瀏覽器打開 `~/.cursor/cursor-token-tracker/ledger.html`。頁面會自己重新整理。預設是繁體中文。把 `en` 寫進 `~/.cursor/cursor-token-tracker/lang` 就改成英文。

本回合是一列，表頭為：未快取輸入、快取讀取、快取寫入、輸出、合計。

本對話累計是第二個表：模型、同樣那幾欄、回合。每個模型一列，最後一列是「全部」。累計只算目前這個對話。

## 安裝

打開這個 repository 就會載入專案 hook（`.cursor/hooks.json`）和專案 skill。

若要在每個專案都用，把使用者層級的 `stop` hook 指到腳本，並連上 skill：

```bash
# ~/.cursor/hooks.json（合併進現有檔案，不要覆蓋其他 hook）
# "stop": [{ "command": "/usr/bin/python3 /絕對路徑/.cursor/hooks/token-tracker.py", "timeout": 10, "loop_limit": 1 }]

ln -sfn /絕對路徑/Cursor_Token_Tracker/.cursor/skills/cursor-token-tracker \
  ~/.cursor/skills/cursor-token-tracker
```

Cursor 會在 `hooks.json` 存檔後重新載入。紀錄在 `~/.cursor/cursor-token-tracker/state.json`。

```bash
/usr/bin/python3 .cursor/hooks/token-tracker.py --selftest
```
