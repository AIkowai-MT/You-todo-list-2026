#!/usr/bin/env bash
#
# sync_vault.sh - vault配下をgit add / commit / push する。
# 変更がなければスキップ。
#
set -euo pipefail

VAULT_DIR="${HOME}/vault"

cd "${VAULT_DIR}"

# gitリポジトリが未初期化なら初期化
if [ ! -d ".git" ]; then
    echo "[WARN] vault は git 管理されていません。git init を実行します。"
    git init
    echo "[INFO] リモートを手動で設定してください: git remote add origin <URL>"
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
    echo "[WARN] リモートが設定されていません。ローカルコミットのみ完了。"
fi
