#!/usr/bin/env bash
#
# sync_vault.sh - vault配下をgit add / commit / push する。
# 変更がなければスキップ（exit 0）。
#
set -euo pipefail

VAULT_DIR="/home/youtube-analyst-bot/vault"

cd "${VAULT_DIR}"

# gitリポジトリが未初期化なら警告して終了
if [ ! -d ".git" ]; then
    echo "[ERROR] ${VAULT_DIR} は git 管理されていません。" >&2
    echo "[ERROR] git clone で bot-yt を配置してください。" >&2
    exit 1
fi

# 変更があるか確認
git add -A

if git diff --cached --quiet; then
    echo "[INFO] 変更なし。スキップします。"
    exit 0
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M')
git commit -m "vault sync ${TIMESTAMP}"

# リモートが設定されていればpush
if git remote get-url origin >/dev/null 2>&1; then
    git push origin HEAD
    echo "[OK] push 完了: vault sync ${TIMESTAMP}"
else
    echo "[WARN] リモートが設定されていません。ローカルコミットのみ完了。" >&2
fi
