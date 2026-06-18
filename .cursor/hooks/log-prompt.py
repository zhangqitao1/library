#!/usr/bin/env python3
"""beforeSubmitPrompt 钩子：把每条用户提问自动归档，用于追踪"她想了解什么"。

设计要点：
- 观察型钩子，绝不能阻断用户发送 —— 任何异常都吞掉并 exit 0、输出空 JSON。
- 不依赖 jq/第三方库，只用标准库，保证在任何环境都能跑。
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

CST = timezone(timedelta(hours=8))
# 日志落在「学情」层（家教的记忆），与档案/复习日志同处
ROOT = Path(__file__).resolve().parents[2]
LOG_FILE = ROOT / "学情" / "提问记录.jsonl"
ERR_FILE = ROOT / "学情" / ".hook-error.log"

# 不同事件/版本字段名可能不同，按优先级探测，避免漏记
PROMPT_KEYS = ("prompt", "user_prompt", "text", "message", "content")
ID_KEYS = ("conversation_id", "chat_id", "session_id", "generation_id")


def extract_prompt(data: dict):
    for k in PROMPT_KEYS:
        v = data.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip(), k
    return None, None


def main():
    raw = sys.stdin.read()
    data = json.loads(raw) if raw.strip() else {}

    prompt, src_key = extract_prompt(data)
    record = {
        "time": datetime.now(CST).isoformat(timespec="seconds"),
        "prompt": prompt,
    }
    for k in ID_KEYS:
        if data.get(k):
            record[k] = data[k]
    # 没识别出提问文本时，留原始键名便于排查字段，不丢信息
    if prompt is None:
        record["_raw_keys"] = list(data.keys())
        record["_raw"] = raw[:2000]
    else:
        record["_src"] = src_key

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # 钩子失败必须 fail-open，否则会拖垮正常对话
        try:
            ERR_FILE.parent.mkdir(parents=True, exist_ok=True)
            with ERR_FILE.open("a", encoding="utf-8") as f:
                f.write(f"{datetime.now(CST).isoformat(timespec='seconds')} {e!r}\n")
        except OSError:
            pass
    print("{}")
    sys.exit(0)
