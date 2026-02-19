# ローカル自動化システム セットアップガイド

## 前提条件

- Python 3.8+
- git
- cron (systemd-timer でも可)

## ディレクトリ構成

```
~/ops/
  tasks.json          # タスク定義
  events.jsonl        # イベントログ (自動追記)
  scripts/
    run_tasks.py      # タスク実行
    daily_digest.py   # デイリーレポート生成
    weekly_report.py  # 週次レポート生成
    label_scan.py     # ステータス別一覧生成
    sync_vault.sh     # Vault Git同期

~/vault/
  00_Inbox/
  10_Daily/           # デイリーレポート
  20_Weekly/          # 週次レポート
  30_Research/
  40_Memory/
  90_Status/          # pending.md, reviewing.md
```

## セットアップ手順

### 1. ディレクトリ作成

```bash
mkdir -p ~/ops/scripts
mkdir -p ~/vault/{00_Inbox,10_Daily,20_Weekly,30_Research,40_Memory,90_Status}
```

### 2. ファイル配置

このリポジトリの `ops/` 配下を `~/ops/` にコピー:

```bash
cp -r ops/* ~/ops/
chmod +x ~/ops/scripts/sync_vault.sh
```

### 3. Vault を Git リポジトリ化

```bash
cd ~/vault
git init
git remote add origin git@github.com:<user>/<private-repo>.git
git add -A
git commit -m "initial vault"
git push -u origin main
```

### 4. tasks.json を編集

`~/ops/tasks.json` を自分のタスクに合わせて編集:

```json
[
  {
    "id": "my_task",
    "title": "タスク名",
    "run": "コマンド",
    "schedule": ["10:00"],
    "labels": ["pending"],
    "project": "プロジェクト名"
  }
]
```

### 5. cron 設定

```bash
crontab -e
```

以下を追記:

```cron
# タスク実行 (10:00, 14:00)
0 10 * * * /usr/bin/python3 ~/ops/scripts/run_tasks.py --time 10:00 >> ~/ops/cron.log 2>&1
0 14 * * * /usr/bin/python3 ~/ops/scripts/run_tasks.py --time 14:00 >> ~/ops/cron.log 2>&1

# デイリーレポート (毎日 23:30)
30 23 * * * /usr/bin/python3 ~/ops/scripts/daily_digest.py >> ~/ops/cron.log 2>&1

# 週次レポート (毎週月曜 09:00)
0 9 * * 1 /usr/bin/python3 ~/ops/scripts/weekly_report.py >> ~/ops/cron.log 2>&1

# ステータス更新 (30分ごと)
*/30 * * * * /usr/bin/python3 ~/ops/scripts/label_scan.py >> ~/ops/cron.log 2>&1

# Vault同期 (毎日 23:35)
35 23 * * * bash ~/ops/scripts/sync_vault.sh >> ~/ops/cron.log 2>&1
```

## 動作確認

### 手動でタスク実行

```bash
python3 ~/ops/scripts/run_tasks.py --time 10:00
```

events.jsonl にイベントが記録されることを確認:

```bash
cat ~/ops/events.jsonl
```

### 手動でデイリーレポート生成

```bash
python3 ~/ops/scripts/daily_digest.py
cat ~/vault/10_Daily/$(date +%Y-%m-%d).md
```

### 手動で週次レポート生成

```bash
python3 ~/ops/scripts/weekly_report.py
ls ~/vault/20_Weekly/
```

### 手動でステータス更新

```bash
python3 ~/ops/scripts/label_scan.py
cat ~/vault/90_Status/pending.md
cat ~/vault/90_Status/reviewing.md
```

### 手動でVault同期

```bash
bash ~/ops/scripts/sync_vault.sh
```

## イベントの手動追加

note や decision を手動で追加する場合:

```bash
echo '{"ts":"'$(date -Iseconds)'","type":"note","meta":{"text":"RSSをWebhook方式に変更"}}' >> ~/ops/events.jsonl
echo '{"ts":"'$(date -Iseconds)'","type":"decision","meta":{"text":"Pythonで実装する"}}' >> ~/ops/events.jsonl
```

## Mac との同期

Obsidian Vault を GitHub Private Repo 経由で同期:

1. VPS側: `sync_vault.sh` が cron で定期的に push
2. Mac側: Obsidian Git プラグインで定期 pull、または cron で `git pull`

```bash
# Mac側のcron例
*/10 * * * * cd ~/vault && git pull origin main 2>&1
```

## 操作ガイド（HELP.md）

`vault/00_Inbox/HELP.md` に Mac/VPS の操作方法・crontab・トラブルシュート情報を
1ファイルにまとめて自動生成します。

### 手動生成

```bash
python3 /home/autobot/ops/scripts/help_guide.py
cat /home/autobot/vault/00_Inbox/HELP.md
```

### cron に追加する場合（任意）

既存の label_scan の直後に追加:

```cron
*/30 * * * * /usr/bin/python3 /home/autobot/ops/scripts/help_guide.py
```

ログを残したい場合は logger を使う方法もあります:

```cron
*/30 * * * * /usr/bin/python3 /home/autobot/ops/scripts/help_guide.py 2>&1 | logger -t help_guide
```

### help_entries.jsonl

新機能を追加したら `/home/autobot/ops/help_entries.jsonl` に1行追記してください。

- 必須フィールド: `feature`, `purpose`, `command`, `output`, `verify`
- 任意フィールド: `how`, `note`
- パス: 全て絶対パス（`/home/autobot/...`）で記述
- `#` で始まる行と空行はスキップされます
