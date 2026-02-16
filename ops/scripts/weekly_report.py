#!/usr/bin/env python3
"""
weekly_report.py - 今週のイベントを集計し、週次レポートを生成する。

出力: ~/vault/20_Weekly/YYYY-WNN.md

内容:
  - 完了タスク数
  - タスク別実行回数
  - 重要 decision 一覧
  - 次週候補 (pending)
"""

import json
import os
from collections import Counter
from datetime import date, datetime, timedelta, timezone

BASE_DIR = os.path.expanduser("~/ops")
VAULT_DIR = os.path.expanduser("~/vault")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
EVENTS_FILE = os.path.join(BASE_DIR, "events.jsonl")


def load_tasks():
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_week_range(target_date: date) -> tuple:
    """対象日を含む週の月曜日と日曜日を返す。"""
    monday = target_date - timedelta(days=target_date.weekday())
    sunday = monday + timedelta(days=6)
    return monday, sunday


def load_events_for_week(monday: date, sunday: date) -> list:
    """指定週のイベントを返す。"""
    events = []
    if not os.path.exists(EVENTS_FILE):
        return events
    mon_str = monday.isoformat()
    sun_str = sunday.isoformat()
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts_date = ev.get("ts", "")[:10]
            if mon_str <= ts_date <= sun_str:
                events.append(ev)
    return events


def build_task_map(tasks: list) -> dict:
    return {t["id"]: t for t in tasks}


def generate_weekly_md(target_date: date) -> tuple:
    """週次レポートのMarkdownとファイル名を返す。"""
    tasks = load_tasks()
    task_map = build_task_map(tasks)
    monday, sunday = get_week_range(target_date)
    events = load_events_for_week(monday, sunday)

    iso_year, iso_week, _ = target_date.isocalendar()
    filename = f"{iso_year}-W{iso_week:02d}.md"

    # 集計
    completed_tasks = []
    task_run_count = Counter()
    decisions = []

    for ev in events:
        etype = ev.get("type")
        if etype == "task_start":
            tid = ev.get("task_id", "unknown")
            task_run_count[tid] += 1
        elif etype == "task_done":
            tid = ev.get("task_id", "unknown")
            exit_code = ev.get("meta", {}).get("exit", -1)
            title = task_map.get(tid, {}).get("title", tid)
            completed_tasks.append({
                "id": tid,
                "title": title,
                "exit": exit_code,
            })
        elif etype == "decision":
            text = ev.get("meta", {}).get("text", "")
            decisions.append({"text": text, "ts": ev["ts"]})

    success_count = sum(1 for t in completed_tasks if t["exit"] == 0)
    fail_count = sum(1 for t in completed_tasks if t["exit"] != 0)

    # 次週候補 (pending)
    pending_tasks = [t for t in tasks if "pending" in t.get("labels", [])]

    # Markdown生成
    lines = []
    lines.append("---")
    lines.append(f"week: {iso_year}-W{iso_week:02d}")
    lines.append(f"period: {monday.isoformat()} ~ {sunday.isoformat()}")
    lines.append("type: weekly")
    lines.append("---")
    lines.append("")
    lines.append(f"# Weekly Report: {iso_year}-W{iso_week:02d}")
    lines.append(f"> {monday.isoformat()} ~ {sunday.isoformat()}")
    lines.append("")

    # サマリ
    lines.append("## サマリ")
    lines.append("")
    lines.append(f"- 完了タスク数: **{success_count}** (失敗: {fail_count})")
    lines.append(f"- 総実行回数: **{sum(task_run_count.values())}**")
    lines.append("")

    # タスク別実行回数
    lines.append("## タスク別実行回数")
    lines.append("")
    if task_run_count:
        lines.append("| タスクID | タスク名 | 実行回数 |")
        lines.append("|----------|----------|----------|")
        for tid, count in task_run_count.most_common():
            title = task_map.get(tid, {}).get("title", tid)
            lines.append(f"| `{tid}` | {title} | {count} |")
    else:
        lines.append("- (実行なし)")
    lines.append("")

    # 完了タスク詳細
    lines.append("## 完了タスク")
    lines.append("")
    if completed_tasks:
        for t in completed_tasks:
            status = "OK" if t["exit"] == 0 else f"FAIL(exit={t['exit']})"
            lines.append(f"- `{t['id']}` {t['title']} — {status}")
    else:
        lines.append("- (なし)")
    lines.append("")

    # Decisions
    lines.append("## 重要 Decisions")
    lines.append("")
    if decisions:
        for d in decisions:
            lines.append(f"- [{d['ts'][:10]}] {d['text']}")
    else:
        lines.append("- (なし)")
    lines.append("")

    # 次週候補
    lines.append("## 次週候補 (Pending)")
    lines.append("")
    if pending_tasks:
        for t in pending_tasks:
            lines.append(f"- `{t['id']}` {t['title']} (project: {t.get('project', '-')})")
    else:
        lines.append("- (なし)")
    lines.append("")

    return "\n".join(lines), filename


def main():
    today = date.today()
    md_content, filename = generate_weekly_md(today)

    output_dir = os.path.join(VAULT_DIR, "20_Weekly")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"[OK] Weekly report written to {output_path}")


if __name__ == "__main__":
    main()
