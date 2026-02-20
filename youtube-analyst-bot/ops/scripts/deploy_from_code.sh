#!/usr/bin/env bash
set -euo pipefail

# ── deploy_from_code.sh（youtube-analyst-bot版）────────────
# /home/youtube-analyst-bot/code/ops/* → /home/youtube-analyst-bot/ops/ へ反映
# 用途: git pull 後に実行してスクリプトを実運用ディレクトリへ同期
# ───────────────────────────────────────────────────────────

CODE_DIR="/home/youtube-analyst-bot/code"
OPS_DIR="/home/youtube-analyst-bot/ops"
SENTINEL="/home/youtube-analyst-bot/ops/scripts/yt_trend_pipeline.sh"

echo "[deploy] $(date '+%Y-%m-%d %H:%M:%S') 開始"

# 1. code 存在チェック
if [ ! -d "${CODE_DIR}" ]; then
  echo "[ERROR] ${CODE_DIR} が見つかりません。処理を中止します。" >&2
  exit 1
fi

if [ ! -d "${CODE_DIR}/ops" ]; then
  echo "[ERROR] ${CODE_DIR}/ops が見つかりません。処理を中止します。" >&2
  exit 1
fi

# 2. ディレクトリ確保
mkdir -p "${OPS_DIR}/scripts"
mkdir -p "${OPS_DIR}/data/youtube/snapshots"

# 3. コピー
cp -r "${CODE_DIR}/ops/"* "${OPS_DIR}/"
echo "[deploy] cp 完了: ${CODE_DIR}/ops/* → ${OPS_DIR}/"

# 4. 反映確認
if [ -f "${SENTINEL}" ]; then
  echo "[deploy] OK: ${SENTINEL} を確認"
else
  echo "[WARN]  NG: ${SENTINEL} が見当たりません" >&2
fi

echo "[deploy] 完了"
