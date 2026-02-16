#!/usr/bin/env python3
"""
run_tasks.py - スケジュールに基づいてタスクを実行し、イベントログに記録する。

Usage:
    python3 run_tasks.py --time 10:00
    python3 run_tasks.py --time 14:00
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.expanduser("~/ops")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
EVENTS_FILE = os.path.join(BASE_DIR, "events.jsonl")


def load_tasks():
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def append_event(event: dict):
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def run_task(task: dict) -> int:
    """タスクを実行し、exit codeを返す。"""
    task_id = task["id"]
    print(f"[START] {task_id}: {task['title']}")

    append_event({
        "ts": now_iso(),
        "type": "task_start",
        "task_id": task_id,
    })

    try:
        result = subprocess.run(
            task["run"],
            shell=True,
            timeout=3600,
            capture_output=True,
            text=True,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        exit_code = -1
        print(f"[TIMEOUT] {task_id}")
    except Exception as e:
        exit_code = -2
        print(f"[ERROR] {task_id}: {e}")

    append_event({
        "ts": now_iso(),
        "type": "task_done",
        "task_id": task_id,
        "meta": {"exit": exit_code},
    })

    status = "OK" if exit_code == 0 else f"FAIL({exit_code})"
    print(f"[DONE]  {task_id}: {status}")
    return exit_code


def main():
    parser = argparse.ArgumentParser(description="スケジュールに基づいてタスクを実行する")
    parser.add_argument("--time", required=True, help="実行時刻 (例: 10:00)")
    args = parser.parse_args()

    target_time = args.time
    tasks = load_tasks()

    matched = [t for t in tasks if target_time in t.get("schedule", [])]

    if not matched:
        print(f"[INFO] {target_time} にスケジュールされたタスクはありません。")
        sys.exit(0)

    print(f"=== {target_time} のタスク実行開始 ({len(matched)}件) ===")
    results = []
    for task in matched:
        exit_code = run_task(task)
        results.append((task["id"], exit_code))

    print(f"\n=== 実行結果サマリ ===")
    for task_id, code in results:
        status = "OK" if code == 0 else f"FAIL({code})"
        print(f"  {task_id}: {status}")

    failures = [r for r in results if r[1] != 0]
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
