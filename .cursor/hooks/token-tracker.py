#!/usr/bin/python3
"""Record parent-agent tokens on Cursor's stop hook and write an HTML table.

Does not return followup_message. That field is submitted as the next user
message and refills the composer. One model per turn. input_tokens already
includes cache read and cache write. Subagent tokens are not in this payload.
Echo turns (loop_count > 0) are skipped.
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
        "note": "此頁在每回合結束後更新，不會送進對話輸入框。",
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
        "note": "This page updates after each turn and is not typed into the chat input.",
    },
}


def state_path():
    override = os.environ.get("CURSOR_TOKEN_TRACKER_STATE")
    if override:
        return Path(override)
    return Path.home() / ".cursor" / "cursor-token-tracker" / "state.json"


def ledger_path():
    return state_path().with_name("ledger.html")


def language():
    path = Path.home() / ".cursor" / "cursor-token-tracker" / "lang"
    try:
        value = path.read_text(encoding="utf-8").strip().lower()
    except OSError:
        return "zh"
    return "en" if value == "en" else "zh"


def fmt(value):
    return f"{value:,}"


def esc(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


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


def html_table(headers, rows):
    head = "".join(f"<th>{esc(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{esc(cell)}</td>" for cell in row)
        body.append(f"<tr>{cells}</tr>")
    return (
        "<table><thead><tr>"
        + head
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


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


def render(turn_no, model, parts, turns, labels):
    shown = model or labels["unknown"]
    headers = [labels[key] for key in (*KEYS[:-1], "total")]
    blocks = [f"<h2>{esc(labels['turn'].format(n=turn_no, model=shown))}</h2>"]
    if parts is None:
        blocks.append(f"<p>{esc(labels['missing'])}</p>")
    else:
        blocks.append(html_table(headers, [[fmt(parts[key]) for key in (*KEYS[:-1], "total")]]))

    blocks.append(f"<h2>{esc(labels['cumulative'])}</h2>")
    order, sums, counts = totals(turns, labels)
    if not order:
        blocks.append(f"<p>{esc(labels['empty'])}</p>")
    else:
        rows = []
        grand = {key: 0 for key in KEYS}
        counted = 0
        for name in order:
            counted += counts[name]
            for key in KEYS:
                grand[key] += sums[name][key]
            rows.append(
                [name] + [fmt(sums[name][key]) for key in KEYS] + [str(counts[name])]
            )
        rows.append([labels["all"]] + [fmt(grand[key]) for key in KEYS] + [str(counted)])
        blocks.append(
            html_table(
                [labels["model"], *headers, labels["rounds"]],
                rows,
            )
        )
    return page("\n".join(blocks), labels)


def page(body, labels):
    return f"""<!DOCTYPE html>
<html lang="{ 'zh-Hant' if labels is LABELS['zh'] else 'en' }">
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="2">
<title>Token</title>
<style>
  body {{ margin: 24px; background: #1e1e1e; color: #e6e6e6; font: 14px/1.4 sans-serif; }}
  h2 {{ font-size: 15px; margin: 20px 0 8px; }}
  p.note {{ color: #9a9a9a; }}
  table {{ border-collapse: collapse; }}
  th, td {{ border: 1px solid #3a3a3a; padding: 6px 12px; text-align: right; }}
  th {{ background: #2a2a2a; }}
  th:first-child, td:first-child {{ text-align: left; }}
</style>
</head>
<body>
<p class="note">{esc(labels['note'])}</p>
{body}
</body>
</html>
"""


def seen_ids(conv):
    found = set(conv.get("seen") or [])
    found.update(conv.get("followups") or {})
    return found


def apply(state, payload, labels):
    if int(payload.get("loop_count") or 0) > 0:
        return None

    conv_id = str(payload.get("conversation_id") or "unknown")
    gen_id = str(payload.get("generation_id") or "")
    conv = state.setdefault("conversations", {}).setdefault(
        conv_id, {"turns": [], "seen": []}
    )
    seen = seen_ids(conv)
    if gen_id and gen_id in seen:
        return None

    parts = token_parts(payload)
    if parts is None:
        fields = ", ".join(sorted(payload))
        print(f"[cursor-token-tracker] no token fields: {fields}", file=sys.stderr)

    model = str(payload.get("model") or payload.get("model_id") or "").strip()
    turn = {"model": model, "has_tokens": parts is not None}
    if parts is not None:
        turn.update(parts)
    conv["turns"].append(turn)
    if gen_id:
        conv.setdefault("seen", [])
        if gen_id not in conv["seen"]:
            conv["seen"].append(gen_id)
    return render(len(conv["turns"]), model, parts, conv["turns"], labels)


def write_ledger(html):
    path = ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


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
        html = apply(state, payload, labels)
        handle_file.seek(0)
        handle_file.truncate()
        handle_file.write(json.dumps(state, ensure_ascii=False, indent=2))
        handle_file.flush()
        fcntl.flock(handle_file, fcntl.LOCK_UN)
    if html:
        write_ledger(html)
    return {}


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
    html = apply(state, first, labels)
    assert html is not None
    assert "<th>未快取輸入</th>" in html and "<th>合計</th>" in html
    assert "1,204" in html and "842,110" in html and "865,656" in html
    assert "<h2>本回合 #1 · grok-4.7</h2>" in html
    assert apply(state, first, labels) is None
    assert len(state["conversations"]["c1"]["turns"]) == 1

    echo = dict(first, generation_id="g-echo", loop_count=1, output_tokens=9)
    assert apply(state, echo, labels) is None
    assert len(state["conversations"]["c1"]["turns"]) == 1

    missing = {
        "conversation_id": "c1",
        "generation_id": "g-missing",
        "model": "grok-4.7",
        "status": "completed",
        "loop_count": 0,
    }
    missing_html = apply(state, missing, labels)
    assert "無 token 資料" in missing_html
    assert "865,656" in missing_html
    assert "<td>1</td>" in missing_html

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
    assert "composer-2.5" in both and "grok-4.7" in both
    assert "<th>模型</th>" in both and "<th>回合</th>" in both
    assert "<td>2</td>" in both

    clamped = token_parts(
        {
            "input_tokens": 10,
            "output_tokens": 1,
            "cache_read_tokens": 8,
            "cache_write_tokens": 8,
        }
    )
    assert clamped["uncached"] == 0 and clamped["total"] == 11

    english = render(
        1, "grok-4.7", token_parts(first), state["conversations"]["c1"]["turns"], LABELS["en"]
    )
    assert "<h2>Turn #1 · grok-4.7</h2>" in english
    assert "<th>uncached input</th>" in english
    assert "conversation total" in english
    assert "followup_message" not in english

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
