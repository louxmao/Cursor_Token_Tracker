# Cursor Token Tracker

[English](README.md)

每個 agent 回合結束後，記錄這一回的 token，以及這個對話依模型分開的累計。

數字來自回合結束時的 `stop` hook（`input_tokens`、`output_tokens`、`cache_read_tokens`、`cache_write_tokens`、`model`）。`input_tokens` 已含兩種快取。未快取輸入是 `input_tokens - cache_read_tokens - cache_write_tokens`，小於 0 就當 0。本回合合計是 `input_tokens + output_tokens`。

`stop` hook 只能把文字當成下一則使用者訊息送出，所以結算會出現在回答後面。Skill 讓 agent 只把這段原樣貼回、然後停止。這次回顯（`loop_count > 0`）不計入累計。每一回只記一個模型。子代理的 token 不在這份資料裡。若沒有 token 欄位，這一回顯示「無 token 資料」，也不把 0 加進累計。

## 畫面上會看到

預設是繁體中文。把 `en` 寫進 `~/.cursor/cursor-token-tracker/lang` 就改成英文。

```
Token · 本回合 #4 · grok-4.7
  未快取輸入      1,204
  快取讀取      842,110
  快取寫入       18,440
  輸出            3,902
  本回合合計    865,656

本對話累計
  grok-4.7      未快取 12,400 · 快取讀 2,100,000 · 快取寫 40,000 · 輸出 18,200 · 合計 2,170,600
  composer-2.5  未快取 3,100 · 快取讀 0 · 快取寫 8,200 · 輸出 1,450 · 合計 12,750
  全部          未快取 15,500 · 快取讀 2,100,000 · 快取寫 48,200 · 輸出 19,650 · 合計 2,183,350 · 4 回合
```

累計只算目前這個對話。

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
