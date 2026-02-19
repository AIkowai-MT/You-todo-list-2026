#!/usr/bin/env bash
set -euo pipefail

# ── bootstrap_ops.sh ─────────────────────────────────────
# 初回セットアップ用: /home/autobot/code/ops/* → /home/autobot/ops/ へ反映
# 実行方法: bash /home/autobot/code/ops/scripts/bootstrap_ops.sh
# 以後の更新は: bash /home/autobot/ops/scripts/deploy_from_code.sh
# ──────────────────────────────────────────────────────────

CODE_DIR="/home/autobot/code"
OPS_DIR="/home/autobot/ops"

echo "[bootstrap] $(date '+%Y-%m-%d %H:%M:%S') 開始"

# 1. code/ops 存在チェック
if [ ! -d "${CODE_DIR}/ops" ]; then
  echo "[ERROR] ${CODE_DIR}/ops が見つかりません。" >&2
  exit 1
fi

# 2. ops ディレクトリ確保
mkdir -p "${OPS_DIR}/scripts"

# 3. コピー
cp -r "${CODE_DIR}/ops/"* "${OPS_DIR}/"
echo "[bootstrap] cp 完了: ${CODE_DIR}/ops/* → ${OPS_DIR}/"

# 4. 反映確認
PASS=0
FAIL=0
for f in deploy_from_code.sh help_guide.py run_tasks.py daily_digest.py; do
  if [ -f "${OPS_DIR}/scripts/${f}" ]; then
    echo "[bootstrap] OK: ${f}"
    PASS=$((PASS + 1))
  else
    echo "[WARN]  NG: ${f} が見当たりません" >&2
    FAIL=$((FAIL + 1))
  fi
done

echo "[bootstrap] 完了 (OK=${PASS}, NG=${FAIL})"
if [ "${FAIL}" -gt 0 ]; then
  echo "[bootstrap] 一部ファイルが欠けています。code/ops/ の内容を確認してください。" >&2
  exit 1
fi

echo "[bootstrap] 以後は bash ${OPS_DIR}/scripts/deploy_from_code.sh で更新できます。"
