#!/usr/bin/python3
"""Record parent-agent tokens and hand the model a plain-text table to append.

stop records the turn and returns no followup_message, so nothing is typed
into the composer. beforeSubmitPrompt passes the finished turns to the model,
which pastes the table at the end of the next reply. One model per turn.
input_tokens already includes cache read and cache write. Subagent tokens are
not in this payload. Echo turns (loop_count > 0) are skipped.
"""

import json
import os
import sys
from pathlib import Path

KEYS = ("uncached", "cache_read", "cache_write", "output", "total")
TOKEN_FIELDS = (
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
)

LABELS = {
    "zh": {
        "turn": "本回合 #{n} · {model}",
        "uncached": "未快取輸入",
        "cache_read": "快取讀取",
        "cache_write": "快取寫入",
        "output": "輸出",
        "total": "合計",
        "missing": "無 token 資料",
        "cumulative": "本對話累計",
        "empty": "尚無 token 資料",
        "all": "全部",
        "model": "模型",
        "rounds": "回合",
        "unknown": "未知模型",
        "short": ("未快取", "快取讀", "快取寫", "輸出", "合計"),
        "tell": "把下面的 markdown 表格原樣接在這次回覆正文的最後。不要改數字，不要加說明，不要放進程式碼框，不要寫進輸入框，不要另外送出訊息。",
    },
    "en": {
        "turn": "Turn #{n} · {model}",
        "uncached": "uncached input",
        "cache_read": "cache read",
        "cache_write": "cache write",
        "output": "output",
        "total": "total",
        "missing": "no token data",
        "cumulative": "conversation total",
        "empty": "no token data yet",
        "all": "all models",
        "model": "model",
        "rounds": "turns",
        "unknown": "unknown model",
        "short": ("uncached", "cache read", "cache write", "output", "total"),
        "tell": "Append the markdown tables below verbatim at the end of this reply. Do not change the numbers, add commentary, wrap them in a code fence, type them into the composer, or send another message.",
    },
}


def state_path():
    override = os.environ.get("CURSOR_TOKEN_TRACKER_STATE")
    if override:
        return Path(override)
    return Path.home() / ".cursor" / "cursor-token-tracker" / "state.json"


def language():
    path = Path.home() / ".cursor" / "cursor-token-tracker" / "lang"
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "zh"
    return "en" if value == "en" else "zh"


def fmt(value):
    return f"{value:,}"


def token_parts(payload):
    values = []
    for key in TOKEN_FIELDS:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        values.append(int(value))
    incoming, output, cache_read, cache_write = values
    return {
        "uncached": max(0, incoming - cache_read - cache_write),
        "cache_read": cache_read,
        "cache_write": cache_write,
        "output": output,
        "total": incoming + output,
    }


def md_table(headers, rows, numeric_from):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---:" if i >= numeric_from else "---" for i in range(len(headers))) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def totals(turns, labels):
    sums = {}
    order = []
    counts = {}
    for turn in turns:
        if not turn["has_tokens"]:
            continue
        name = turn["model"] or labels["unknown"]
        bucket = sums.get(name)
        if bucket is None:
            order.append(name)
            bucket = {key: 0 for key in KEYS}
            sums[name] = bucket
            counts[name] = 0
        counts[name] += 1
        for key in KEYS:
            bucket[key] += turn[key]
    return order, sums, counts


def ledger_text(turns, labels):
    last = turns[-1]
    shown = last.get("model") or labels["unknown"]
    parts = last if last.get("has_tokens") else None
    lines = [labels["turn"].format(n=len(turns), model=shown), ""]
    headers = [labels[key] for key in (*KEYS[:-1], "total")]
    if parts is None:
        lines.append(labels["missing"])
    else:
        lines.append(md_table(headers, [[fmt(parts[key]) for key in (*KEYS[:-1], "total")]], 0))
    lines.extend(["", labels["cumulative"], ""])
    order, sums, counts = totals(turns, labels)
    if not order:
        lines.append(labels["empty"])
        return "\n".join(lines)
    rows = []
    grand = {key: 0 for key in KEYS}
    counted = 0
    for name in order:
        counted += counts[name]
        for key in KEYS:
            grand[key] += sums[name][key]
        rows.append([name] + [fmt(sums[name][key]) for key in KEYS] + [str(counts[name])])
    rows.append([labels["all"]] + [fmt(grand[key]) for key in KEYS] + [str(counted)])
    lines.append(md_table([labels["model"], *labels["short"], labels["rounds"]], rows, 1))
    return "\n".join(lines)


def context_for(turns, labels):
    if not turns:
        return {}
    return {"additional_context": labels["tell"] + "\n\n" + ledger_text(turns, labels)}


def seen_ids(conv):
    found = set(conv.get("seen") or [])
    found.update(conv.get("followups") or {})
    return found


def apply(state, payload, labels):
    if int(payload.get("loop_count") or 0) > 0:
        return None
    conv_id = str(payload.get("conversation_id") or "unknown")
    gen_id = str(payload.get("generation_id") or "")
    conv = state.setdefault("conversations", {}).setdefault(conv_id, {"turns": [], "seen": []})
    if gen_id and gen_id in seen_ids(conv):
        return None
    parts = token_parts(payload)
    if parts is None:
        print(
            "[cursor-token-tracker] no token fields: " + ", ".join(sorted(payload)),
            file=sys.stderr,
        )
    model = str(payload.get("model") or payload.get("model_id") or "").strip()
    turn = {"model": model, "has_tokens": parts is not None}
    if parts is not None:
        turn.update(parts)
    conv["turns"].append(turn)
    if gen_id and gen_id not in conv.setdefault("seen", []):
        conv["seen"].append(gen_id)
    return ledger_text(conv["turns"], labels)


def load_state():
    import fcntl

    path = state_path()
    if not path.exists():
        return {"conversations": {}}
    with path.open("r", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        raw = handle.read()
        fcntl.flock(handle, fcntl.LOCK_UN)
    return json.loads(raw) if raw.strip() else {"conversations": {}}


def handle(payload, labels=None):
    import fcntl

    labels = labels or LABELS[language()]
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as handle_file:
        fcntl.flock(handle_file, fcntl.LOCK_EX)
        handle_file.seek(0)
        raw = handle_file.read()
        state = json.loads(raw) if raw.strip() else {"conversations": {}}
        text = apply(state, payload, labels)
        handle_file.seek(0)
        handle_file.truncate()
        handle_file.write(json.dumps(state, ensure_ascii=False, indent=2))
        handle_file.flush()
        fcntl.flock(handle_file, fcntl.LOCK_UN)
    if text:
        path.with_name("latest.txt").write_text(text + "\n", encoding="utf-8")
    return {}


def submit_context(payload, labels=None):
    labels = labels or LABELS[language()]
    conv_id = str(payload.get("conversation_id") or "")
    turns = (load_state().get("conversations") or {}).get(conv_id, {}).get("turns") or []
    return context_for(turns, labels)


def is_prompt(payload):
    name = payload.get("hook_event_name")
    if name == "beforeSubmitPrompt":
        return True
    if name == "stop":
        return False
    return "prompt" in payload and "status" not in payload


def selftest():
    labels = LABELS["zh"]
    state = {"conversations": {}}
    first = {
        "conversation_id": "c1",
        "generation_id": "g1",
        "model": "grok-4.7",
        "status": "completed",
        "loop_count": 0,
        "input_tokens": 1204 + 842110 + 18440,
        "output_tokens": 3902,
        "cache_read_tokens": 842110,
        "cache_write_tokens": 18440,
    }
    text = apply(state, first, labels)
    assert text.startswith("本回合 #1 · grok-4.7"), text
    assert "| 未快取輸入 | 快取讀取 | 快取寫入 | 輸出 | 合計 |" in text
    assert "1,204" in text and "842,110" in text and "865,656" in text
    assert apply(state, first, labels) is None
    assert len(state["conversations"]["c1"]["turns"]) == 1
    echo = dict(first, generation_id="g-echo", loop_count=1, output_tokens=9)
    assert apply(state, echo, labels) is None

    missing = {
        "conversation_id": "c1",
        "generation_id": "g-missing",
        "model": "grok-4.7",
        "status": "completed",
        "loop_count": 0,
    }
    missing_text = apply(state, missing, labels)
    assert "無 token 資料" in missing_text and "865,656" in missing_text

    second = {
        "conversation_id": "c1",
        "generation_id": "g2",
        "model": "composer-2.5",
        "status": "completed",
        "loop_count": 0,
        "input_tokens": 3100 + 8200,
        "output_tokens": 1450,
        "cache_read_tokens": 0,
        "cache_write_tokens": 8200,
    }
    both = apply(state, second, labels)
    assert "| 模型 | 未快取 | 快取讀 | 快取寫 | 輸出 | 合計 | 回合 |" in both
    assert "composer-2.5" in both and "| 2 |" in both

    clamped = token_parts(
        {
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read_tokens": 8,
            "cache_write_tokens": 8,
        }
    )
    assert clamped["uncached"] == 0 and clamped["total"] == 11

    ctx = context_for(state["conversations"]["c1"]["turns"], labels)
    assert "additional_context" in ctx and "followup_message" not in ctx
    assert "不要寫進輸入框" in ctx["additional_context"]
    english = ledger_text(state["conversations"]["c1"]["turns"], LABELS["en"])
    assert english.startswith("Turn #") and "| uncached input |" in english
    assert is_prompt({"hook_event_name": "beforeSubmitPrompt", "prompt": "hi"})
    assert not is_prompt({"hook_event_name": "stop", "status": "completed"})
    print("ok")


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        selftest()
        return
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        sys.stdout.write("{}\n")
        return
    try:
        result = submit_context(payload) if is_prompt(payload) else handle(payload)
    except Exception as error:
        print(f"[cursor-token-tracker] {error}", file=sys.stderr)
        result = {}
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
