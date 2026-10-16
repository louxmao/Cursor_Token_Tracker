#!/usr/bin/python3
"""Record parent-agent tokens on Cursor's stop hook and show the ledger.

One model per turn. input_tokens already includes cache read and cache write.
Subagent tokens are not in this payload. Echo turns (loop_count > 0) are skipped.
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
        "turn": "Token · 本回合 #{n} · {model}",
        "uncached": "未快取輸入",
        "cache_read": "快取讀取",
        "cache_write": "快取寫入",
        "output": "輸出",
        "total": "本回合合計",
        "missing": "無 token 資料",
        "cumulative": "本對話累計",
        "empty": "尚無 token 資料",
        "all": "全部",
        "rounds": "{n} 回合",
        "unknown": "未知模型",
        "uncached_short": "未快取",
        "cache_read_short": "快取讀",
        "cache_write_short": "快取寫",
        "output_short": "輸出",
        "total_short": "合計",
    },
    "en": {
        "turn": "Token · turn #{n} · {model}",
        "uncached": "uncached input",
        "cache_read": "cache read",
        "cache_write": "cache write",
        "output": "output",
        "total": "turn total",
        "missing": "no token data",
        "cumulative": "conversation total",
        "empty": "no token data yet",
        "all": "all models",
        "rounds": "{n} turns",
        "unknown": "unknown model",
        "uncached_short": "uncached",
        "cache_read_short": "cache read",
        "cache_write_short": "cache write",
        "output_short": "output",
        "total_short": "total",
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


def display_width(text):
    return sum(2 if ord(ch) > 127 else 1 for ch in text)


def pad(text, width):
    return text + " " * max(0, width - display_width(text))


def token_parts(payload):
    values = []
    for key in TOKEN_FIELDS:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        values.append(int(value))
    incoming, output, cache_read, cache_write = values
    uncached = max(0, incoming - cache_read - cache_write)
    return {
        "uncached": uncached,
        "cache_read": cache_read,
        "cache_write": cache_write,
        "output": output,
        "total": incoming + output,
    }


def render(turn_no, model, parts, turns, labels):
    shown = model or labels["unknown"]
    lines = [labels["turn"].format(n=turn_no, model=shown)]
    if parts is None:
        lines.append(f"  {labels['missing']}")
    else:
        rows = [(labels[key], parts[key]) for key in (*KEYS[:-1], "total")]
        label_width = max(display_width(label) for label, _ in rows)
        number_width = max(len(fmt(value)) for _, value in rows)
        for label, value in rows:
            lines.append(f"  {pad(label, label_width)}  {fmt(value):>{number_width}}")

    lines.append("")
    lines.append(labels["cumulative"])
    sums = {}
    order = []
    counted = 0
    for turn in turns:
        if not turn["has_tokens"]:
            continue
        counted += 1
        name = turn["model"] or labels["unknown"]
        bucket = sums.get(name)
        if bucket is None:
            order.append(name)
            bucket = {key: 0 for key in KEYS}
            sums[name] = bucket
        for key in KEYS:
            bucket[key] += turn[key]
    if not order:
        lines.append(f"  {labels['empty']}")
        return "\n".join(lines)

    names = order + [labels["all"]]
    width = max(display_width(name) for name in names)
    grand = {key: 0 for key in KEYS}
    for name in order:
        lines.append(model_line(name, sums[name], width, labels))
        for key in KEYS:
            grand[key] += sums[name][key]
    extra = " · " + labels["rounds"].format(n=counted)
    lines.append(model_line(labels["all"], grand, width, labels, extra))
    return "\n".join(lines)


def model_line(name, sums, width, labels, extra=""):
    return (
        f"  {pad(name, width)}  "
        f"{labels['uncached_short']} {fmt(sums['uncached'])} · "
        f"{labels['cache_read_short']} {fmt(sums['cache_read'])} · "
        f"{labels['cache_write_short']} {fmt(sums['cache_write'])} · "
        f"{labels['output_short']} {fmt(sums['output'])} · "
        f"{labels['total_short']} {fmt(sums['total'])}{extra}"
    )


def apply(state, payload, labels):
    if int(payload.get("loop_count") or 0) > 0:
        return {}

    conv_id = str(payload.get("conversation_id") or "unknown")
    gen_id = str(payload.get("generation_id") or "")
    conv = state.setdefault("conversations", {}).setdefault(
        conv_id, {"turns": [], "followups": {}}
    )
    if gen_id and gen_id in conv["followups"]:
        message = conv["followups"][gen_id]
        return {"followup_message": message} if message else {}

    parts = token_parts(payload)
    if parts is None:
        fields = ", ".join(sorted(payload))
        print(f"[cursor-token-tracker] no token fields: {fields}", file=sys.stderr)

    model = str(payload.get("model") or payload.get("model_id") or "").strip()
    turn = {"model": model, "has_tokens": parts is not None}
    if parts is not None:
        turn.update(parts)
    conv["turns"].append(turn)

    text = render(len(conv["turns"]), model, parts, conv["turns"], labels)
    completed = (payload.get("status") or "completed") == "completed"
    if gen_id:
        conv["followups"][gen_id] = text if completed else ""
    if not completed:
        return {}
    return {"followup_message": text}


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
        result = apply(state, payload, labels)
        handle_file.seek(0)
        handle_file.truncate()
        handle_file.write(json.dumps(state, ensure_ascii=False, indent=2))
        handle_file.flush()
        fcntl.flock(handle_file, fcntl.LOCK_UN)
    return result


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
    message = apply(state, first, labels)["followup_message"]
    assert message.startswith("Token · 本回合 #1 · grok-4.7"), message
    assert "1,204" in message and "842,110" in message and "865,656" in message
    again = apply(state, first, labels)["followup_message"]
    assert again == message
    assert len(state["conversations"]["c1"]["turns"]) == 1

    echo = dict(first, generation_id="g-echo", loop_count=1, output_tokens=9)
    assert apply(state, echo, labels) == {}
    assert len(state["conversations"]["c1"]["turns"]) == 1

    missing = {
        "conversation_id": "c1",
        "generation_id": "g-missing",
        "model": "grok-4.7",
        "status": "completed",
        "loop_count": 0,
    }
    missing_text = apply(state, missing, labels)["followup_message"]
    assert "無 token 資料" in missing_text
    assert "865,656" in missing_text
    assert missing_text.strip().endswith("1 回合")

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
    both = apply(state, second, labels)["followup_message"]
    assert "composer-2.5" in both and "grok-4.7" in both
    assert both.strip().endswith("2 回合")

    clamped = token_parts(
        {
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read_tokens": 8,
            "cache_write_tokens": 8,
        }
    )
    assert clamped["uncached"] == 0 and clamped["total"] == 11

    english = render(1, "grok-4.7", token_parts(first), state["conversations"]["c1"]["turns"], LABELS["en"])
    assert english.startswith("Token · turn #1 · grok-4.7"), english
    assert "conversation total" in english

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
        result = handle(payload)
    except Exception as error:
        print(f"[cursor-token-tracker] {error}", file=sys.stderr)
        result = {}
    sys.stdout.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
