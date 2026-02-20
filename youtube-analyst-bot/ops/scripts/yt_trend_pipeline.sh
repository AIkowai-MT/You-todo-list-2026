#!/usr/bin/env bash
# yt_trend_pipeline.sh - YouTube トレンド取得→レポート生成→Vault同期
#
# 入口はこの1本。sudoers で許可されるスクリプト。
#
# Usage:
#   bash /home/youtube-analyst-bot/ops/scripts/yt_trend_pipeline.sh
#   bash /home/youtube-analyst-bot/ops/scripts/yt_trend_pipeline.sh --date 2026-02-19
#
set -euo pipefail

SCRIPTS_DIR="/home/youtube-analyst-bot/ops/scripts"
DATE_ARG=""

# 引数パース（--date YYYY-MM-DD）
while [[ $# -gt 0 ]]; do
    case "$1" in
        --date)
            DATE_ARG="$2"
            shift 2
            ;;
        *)
            echo "[ERROR] 不明な引数: $1" >&2
            exit 1
            ;;
    esac
done

# 日付が未指定なら今日
if [ -z "${DATE_ARG}" ]; then
    DATE_ARG=$(date +%Y-%m-%d)
fi

echo "========================================="
echo " YouTube Trend Pipeline: ${DATE_ARG}"
echo "========================================="

# ── Step 1: API取得 → JSONL保存 ──
echo ""
echo "[STEP 1/3] fetch mostPopular ..."
python3 "${SCRIPTS_DIR}/yt_fetch_mostpopular.py" --date "${DATE_ARG}"

# ── Step 2: JSONL差分 → Markdown生成 ──
echo ""
echo "[STEP 2/3] generate report ..."
python3 "${SCRIPTS_DIR}/yt_trends_report.py" --date "${DATE_ARG}"

# ── Step 3: Vault同期（git push） ──
echo ""
echo "[STEP 3/3] sync vault ..."
bash "${SCRIPTS_DIR}/sync_vault.sh"

echo ""
echo "[PIPELINE] 完了: ${DATE_ARG}"
