#!/usr/bin/env python3
"""
daily_digest.py - 当日のイベントを集計し、デイリーレポートを生成する。

出力: ~/vault/10_Daily/YYYY-MM-DD.md

内容:
  - 実行されたタスク一覧
  - 完了タスク
  - pending / reviewing 一覧
  - 当日の note / decision
"""

import json
import os
from collections import defaultdict
from datetime import date, datetime, timezone

BASE_DIR = os.path.expanduser("~/ops")
VAULT_DIR = os.path.expanduser("~/vault")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
EVENTS_FILE = os.path.join(BASE_DIR, "events.jsonl")


def load_tasks():
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def load_events_for_date(target_date: str) -> list:
    """指定日のイベントを返す。target_date は 'YYYY-MM-DD' 形式。"""
    events = []
    if not os.path.exists(EVENTS_FILE):
        return events
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = ev.get("ts", "")
            if ts[:10] == target_date:
                events.append(ev)
    return events


def build_task_map(tasks: list) -> dict:
    return {t["id"]: t for t in tasks}


def generate_daily_md(target_date: str) -> str:
    tasks = load_tasks()
    task_map = build_task_map(tasks)
    events = load_events_for_date(target_date)

    # 集計
    started_tasks = []
    completed_tasks = []
    notes = []
    decisions = []

    for ev in events:
        etype = ev.get("type")
        if etype == "task_start":
            tid = ev.get("task_id", "unknown")
            title = task_map.get(tid, {}).get("title", tid)
            started_tasks.append({"id": tid, "title": title, "ts": ev["ts"]})
        elif etype == "task_done":
            tid = ev.get("task_id", "unknown")
            title = task_map.get(tid, {}).get("title", tid)
            exit_code = ev.get("meta", {}).get("exit", -1)
            completed_tasks.append({
                "id": tid,
                "title": title,
                "exit": exit_code,
                "ts": ev["ts"],
            })
        elif etype == "note":
            text = ev.get("meta", {}).get("text", "")
            notes.append({"text": text, "ts": ev["ts"]})
        elif etype == "decision":
            text = ev.get("meta", {}).get("text", "")
            decisions.append({"text": text, "ts": ev["ts"]})

    # pending / reviewing をtasks.jsonから取得
    pending_tasks = [t for t in tasks if "pending" in t.get("labels", [])]
    reviewing_tasks = [t for t in tasks if "reviewing" in t.get("labels", [])]

    # Markdown生成
    lines = []
    lines.append("---")
    lines.append(f"date: {target_date}")
    lines.append("type: daily")
    lines.append("---")
    lines.append("")
    lines.append(f"# Daily Report: {target_date}")
    lines.append("")

    # 実行タスク
    lines.append("## 実行タスク")
    lines.append("")
    if started_tasks:
        for t in started_tasks:
            lines.append(f"- `{t['id']}` {t['title']}")
    else:
        lines.append("- (なし)")
    lines.append("")

    # 完了タスク
    lines.append("## 完了タスク")
    lines.append("")
    if completed_tasks:
        for t in completed_tasks:
            status = "OK" if t["exit"] == 0 else f"FAIL(exit={t['exit']})"
            lines.append(f"- `{t['id']}` {t['title']} — {status}")
    else:
        lines.append("- (なし)")
    lines.append("")

    # Pending
    lines.append("## Pending タスク")
    lines.append("")
    if pending_tasks:
        for t in pending_tasks:
            lines.append(f"- `{t['id']}` {t['title']} (project: {t.get('project', '-')})")
    else:
        lines.append("- (なし)")
    lines.append("")

    # Reviewing
    lines.append("## Reviewing タスク")
    lines.append("")
    if reviewing_tasks:
        for t in reviewing_tasks:
            lines.append(f"- `{t['id']}` {t['title']} (project: {t.get('project', '-')})")
    else:
        lines.append("- (なし)")
    lines.append("")

    # Notes
    lines.append("## Notes")
    lines.append("")
    if notes:
        for n in notes:
            lines.append(f"- {n['text']}")
    else:
        lines.append("- (なし)")
    lines.append("")

    # Decisions
    lines.append("## Decisions")
    lines.append("")
    if decisions:
        for d in decisions:
            lines.append(f"- {d['text']}")
    else:
        lines.append("- (なし)")
    lines.append("")

    return "\n".join(lines)


def main():
    today = date.today().isoformat()
    md_content = generate_daily_md(today)

    output_dir = os.path.join(VAULT_DIR, "10_Daily")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{today}.md")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[OK] Daily digest written to {output_path}")


if __name__ == "__main__":
    main()
