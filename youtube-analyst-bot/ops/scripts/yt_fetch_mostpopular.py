#!/usr/bin/env python3
"""yt_fetch_mostpopular.py - YouTube mostPopular をカテゴリ別に取得し JSONL 保存.

Usage:
    python3 yt_fetch_mostpopular.py
    python3 yt_fetch_mostpopular.py --date 2026-02-19

出力: /home/youtube-analyst-bot/ops/data/youtube/snapshots/YYYY-MM-DD.jsonl
"""

import argparse
import sys
import time
from datetime import date

from yt_common import (
    CATEGORIES,
    fetch_most_popular,
    load_api_key,
    now_jst,
    save_snapshot,
)

SLEEP_BETWEEN = 0.3  # カテゴリ間の待機秒数


def main():
    parser = argparse.ArgumentParser(
        description="YouTube mostPopular をカテゴリ別に取得し JSONL 保存"
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="対象日 YYYY-MM-DD（省略時: 今日）",
    )
    args = parser.parse_args()
    date_str = args.date

    api_key = load_api_key()
    fetch_ts = now_jst().isoformat()

    all_records = []
    success_count = 0
    skip_count = 0

    for cat in CATEGORIES:
        print(f"[FETCH] {cat['name']} (id={cat['id']}) ...")
        items = fetch_most_popular(api_key, cat["id"])

        if not items:
            print(f"[SKIP]  {cat['name']}: 0件（APIエラーまたはデータなし）")
            skip_count += 1
            time.sleep(SLEEP_BETWEEN)
            continue

        for item in items:
            snippet = item.get("snippet", {})
            stats = item.get("statistics", {})
            rec = {
                "video_id": item.get("id", ""),
                "category_id": cat["id"],
                "category_name": cat["name"],
                "category_slug": cat["slug"],
                "title": snippet.get("title", ""),
                "channel_title": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "view_count": int(stats.get("viewCount", 0)),
                "like_count": int(stats.get("likeCount", 0)) if stats.get("likeCount") else None,
                "comment_count": int(stats.get("commentCount", 0)) if stats.get("commentCount") else None,
                "fetched_at": fetch_ts,
                "date": date_str,
            }
            all_records.append(rec)

        print(f"[OK]    {cat['name']}: {len(items)}件")
        success_count += 1
        time.sleep(SLEEP_BETWEEN)

    if not all_records:
        print("[ERROR] 1カテゴリも取得できませんでした。", file=sys.stderr)
        sys.exit(1)

    path = save_snapshot(all_records, date_str)
    print(f"\n[DONE] {len(all_records)}件保存 → {path}")
    print(f"       成功: {success_count}カテゴリ / スキップ: {skip_count}カテゴリ")


if __name__ == "__main__":
    main()
