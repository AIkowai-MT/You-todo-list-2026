#!/usr/bin/env python3
"""
label_scan.py - tasks.json のラベルを走査し、ステータス別Markdownを生成する。

出力:
  ~/vault/90_Status/pending.md
  ~/vault/90_Status/reviewing.md
"""

import json
import os
from datetime import datetime, timezone

BASE_DIR = os.path.expanduser("~/ops")
VAULT_DIR = os.path.expanduser("~/vault")
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")


def load_tasks():
    with open(TASKS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat()


def generate_status_md(tasks: list, label: str) -> str:
    filtered = [t for t in tasks if label in t.get("labels", [])]

    lines = []
    lines.append("---")
    lines.append(f"status: {label}")
    lines.append(f"updated: {now_iso()}")
    lines.append("type: status")
    lines.append("---")
    lines.append("")
    lines.append(f"# {label.capitalize()} タスク一覧")
    lines.append("")

    if not filtered:
        lines.append("- (なし)")
        lines.append("")
        return "\n".join(lines)

    # プロジェクト別にグルーピング
    by_project = {}
    for t in filtered:
        proj = t.get("project", "その他")
        by_project.setdefault(proj, []).append(t)

    for proj, proj_tasks in sorted(by_project.items()):
        lines.append(f"## {proj}")
        lines.append("")
        for t in proj_tasks:
            schedule_str = ", ".join(t.get("schedule", []))
            lines.append(f"- `{t['id']}` **{t['title']}**")
            if schedule_str:
                lines.append(f"  - スケジュール: {schedule_str}")
            other_labels = [l for l in t.get("labels", []) if l != label]
            if other_labels:
                lines.append(f"  - ラベル: {', '.join(other_labels)}")
        lines.append("")

    return "\n".join(lines)


def main():
    tasks = load_tasks()
    output_dir = os.path.join(VAULT_DIR, "90_Status")
    os.makedirs(output_dir, exist_ok=True)

    for label in ("pending", "reviewing"):
        md_content = generate_status_md(tasks, label)
        output_path = os.path.join(output_dir, f"{label}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md_content)
        print(f"[OK] {label}.md written to {output_path}")


if __name__ == "__main__":
    main()
