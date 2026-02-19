#!/usr/bin/env python3
"""操作ガイド (HELP.md) 自動生成スクリプト.

ops/help_entries.jsonl を読み込み、vault/00_Inbox/HELP.md を生成する。
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── パス解決 ──────────────────────────────────────────────
OPS_DIR = Path(__file__).resolve().parent.parent          # ops/
ENTRIES_FILE = OPS_DIR / "help_entries.jsonl"
VAULT_DIR = OPS_DIR.parent / "vault"
OUTPUT_FILE = VAULT_DIR / "00_Inbox" / "HELP.md"

REQUIRED_FIELDS = {"feature", "purpose", "command", "output", "verify"}


# ── ヘルパー ──────────────────────────────────────────────
def load_entries(path: Path):
    """help_entries.jsonl を読み込み、エントリと警告を返す。

    空行と # で始まる行はスキップする。
    """
    entries = []
    warnings = []
    with open(path, encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                warnings.append(f"行 {lineno}: JSONパース失敗 ({e})")
                continue
            missing = REQUIRED_FIELDS - set(entry.keys())
            if missing:
                warnings.append(
                    f"行 {lineno}: フィールド {', '.join(sorted(missing))} が欠けています"
                    f'（feature: "{entry.get("feature", "?")}"）'
                )
            entries.append(entry)
    return entries, warnings


def get_crontab() -> str:
    """現在のユーザーの crontab を取得する。"""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.rstrip()
        return f"(取得失敗: crontab -l exited with {result.returncode})"
    except Exception as e:
        return f"(取得失敗: {e})"


def get_vault_remote(vault_dir: Path) -> str:
    """vault の git remote origin URL を動的取得する。"""
    try:
        result = subprocess.run(
            ["git", "-C", str(vault_dir), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return f"(取得失敗: git remote get-url exited with {result.returncode})"
    except Exception as e:
        return f"(取得失敗: {e})"


def render_feature(entry: dict) -> str:
    """1つの機能エントリを Markdown セクションとして描画する。"""
    lines = []
    lines.append(f'### {entry.get("feature", "?")}')
    lines.append(f'- **目的**: {entry.get("purpose", "?")}')
    lines.append("- **実行**:")
    lines.append("  ```bash")
    lines.append(f'  {entry.get("command", "?")}')
    lines.append("  ```")
    lines.append(f'- **出力先**: `{entry.get("output", "?")}`')
    lines.append("- **確認**:")
    lines.append("  ```bash")
    lines.append(f'  {entry.get("verify", "?")}')
    lines.append("  ```")
    if entry.get("how"):
        lines.append(f'- **自動実行**: {entry["how"]}')
    if entry.get("note"):
        lines.append(f'- **備考**: {entry["note"]}')
    return "\n".join(lines)


# ── メイン ────────────────────────────────────────────────
def main():
    if not ENTRIES_FILE.exists():
        print(f"ERROR: {ENTRIES_FILE} が見つかりません", file=sys.stderr)
        sys.exit(1)

    entries, warnings = load_entries(ENTRIES_FILE)
    crontab_output = get_crontab()
    vault_remote = get_vault_remote(VAULT_DIR)
    generated = datetime.now().astimezone().isoformat()

    # 機能一覧セクション
    features_md = "\n\n".join(render_feature(e) for e in entries)

    md = f"""\
---
title: 操作ガイド
generated: "{generated}"
type: help
---

# 操作ガイド

> 自動生成: {generated}
> 手動再生成: `python3 /home/autobot/ops/scripts/help_guide.py`

---

## Mac 側

- **Vault**: `~/bot-vault`
- **Pull スクリプト**: `~/bin/bot_vault_pull.sh`
- **launchd plist**: `~/Library/LaunchAgents/com.mitsuki.botvault.pull.plist`
  - 動作: `cd "$HOME"; "$HOME/bin/bot_vault_pull.sh"` を実行
- **ログ**:
  - stdout: `~/Library/Logs/botvault_pull.log`
  - stderr: `~/Library/Logs/botvault_pull.err`
- **確認する場所**:
  - `10_Daily/` — 日次レポート
  - `20_Weekly/` — 週次レポート
  - `90_Status/` — ラベル別一覧
  - `00_Inbox/` — HELP.md 等

---

## VPS 側

- **ユーザー**: `autobot`
- **タスク定義**: `/home/autobot/ops/tasks.json`
- **イベントログ**: `/home/autobot/ops/events.jsonl`
- **Vault**: `/home/autobot/vault/`
- **Vault remote**: `{vault_remote}`
- **操作エントリ定義**: `/home/autobot/ops/help_entries.jsonl`

---

## 機能一覧

{features_md}

---

## crontab（現在の設定）

> **注意**: 以下は help_guide.py を実行したユーザーの crontab です。
> 通常は autobot ユーザーで実行します。

```
{crontab_output}
```

---

## 困ったときチェック

- **cron が動いているか**:
  ```bash
  systemctl status cron
  ```
- **cron ログ確認**:
  ```bash
  grep CRON /var/log/syslog | tail -20
  ```
- **最新イベント**:
  ```bash
  tail -10 /home/autobot/ops/events.jsonl
  ```
- **Vault の git 状態**:
  ```bash
  cd /home/autobot/vault && git status
  ```
- **手動タスク実行**:
  ```bash
  python3 /home/autobot/ops/scripts/run_tasks.py --time HH:MM
  ```
"""

    # 警告セクション（必須フィールド欠損がある場合のみ）
    if warnings:
        md += "\n---\n\n## 警告\n\n"
        for w in warnings:
            md += f"- {w}\n"

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(md, encoding="utf-8")
    print(f"生成完了: {OUTPUT_FILE}")

    if warnings:
        print(f"警告 {len(warnings)} 件:", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)


if __name__ == "__main__":
    main()
