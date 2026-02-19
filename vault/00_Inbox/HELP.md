---
title: 操作ガイド
generated: "2026-02-19T06:06:02.006652+00:00"
type: help
---

# 操作ガイド

> 自動生成: 2026-02-19T06:06:02.006652+00:00
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
- **Vault remote**: `http://local_proxy@127.0.0.1:34028/git/AIkowai-MT/You-todo-list-2026`
- **操作エントリ定義**: `/home/autobot/ops/help_entries.jsonl`

---

## 機能一覧

### タスク自動実行
- **目的**: 定時にタスクを実行しイベントログに記録
- **実行**:
  ```bash
  python3 /home/autobot/ops/scripts/run_tasks.py --time 10:00
  ```
- **出力先**: `/home/autobot/ops/events.jsonl`
- **確認**:
  ```bash
  tail -5 /home/autobot/ops/events.jsonl
  ```
- **自動実行**: cron が 10:00/14:00 に自動実行
- **備考**: tasks.json で schedule を編集

### 日次レポート
- **目的**: 当日のイベントからデイリーレポートを生成
- **実行**:
  ```bash
  python3 /home/autobot/ops/scripts/daily_digest.py
  ```
- **出力先**: `/home/autobot/vault/10_Daily/YYYY-MM-DD.md`
- **確認**:
  ```bash
  ls /home/autobot/vault/10_Daily/
  ```
- **自動実行**: cron が 23:30 に自動実行
- **備考**: events.jsonl が空だと中身が少ない

### 週次レポート
- **目的**: 1週間のタスク実行メトリクスを集計
- **実行**:
  ```bash
  python3 /home/autobot/ops/scripts/weekly_report.py
  ```
- **出力先**: `/home/autobot/vault/20_Weekly/YYYY-WNN.md`
- **確認**:
  ```bash
  ls /home/autobot/vault/20_Weekly/
  ```
- **自動実行**: cron が毎週月曜 09:00 に自動実行
- **備考**: ISO週(月〜日)で集計

### ラベルスキャン
- **目的**: タスクをラベル別に一覧生成
- **実行**:
  ```bash
  python3 /home/autobot/ops/scripts/label_scan.py
  ```
- **出力先**: `/home/autobot/vault/90_Status/{pending,reviewing}.md`
- **確認**:
  ```bash
  cat /home/autobot/vault/90_Status/pending.md
  ```
- **自動実行**: cron が */30 で自動実行
- **備考**: tasks.json の labels を参照

### Vault同期
- **目的**: vaultをgit pushでMacと同期
- **実行**:
  ```bash
  bash /home/autobot/ops/scripts/sync_vault.sh
  ```
- **出力先**: `/home/autobot/vault/ (git push)`
- **確認**:
  ```bash
  cd /home/autobot/vault && git log --oneline -3
  ```
- **自動実行**: cron が 23:35 に自動実行

### 操作ガイド生成
- **目的**: 操作方法まとめ(HELP.md)を自動生成
- **実行**:
  ```bash
  python3 /home/autobot/ops/scripts/help_guide.py
  ```
- **出力先**: `/home/autobot/vault/00_Inbox/HELP.md`
- **確認**:
  ```bash
  grep '## Mac' /home/autobot/vault/00_Inbox/HELP.md
  ```
- **自動実行**: 手動 or cron(label_scan直後)
- **備考**: help_entries.jsonl から生成

---

## crontab（現在の設定）

> **注意**: 以下は help_guide.py を実行したユーザーの crontab です。
> 通常は autobot ユーザーで実行します。

```
(取得失敗: [Errno 2] No such file or directory: 'crontab')
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
