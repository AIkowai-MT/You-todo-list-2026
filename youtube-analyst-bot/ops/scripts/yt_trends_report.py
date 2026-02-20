#!/usr/bin/env python3
"""yt_trends_report.py - スナップショット差分から Markdown レポートを生成.

Usage:
    python3 yt_trends_report.py
    python3 yt_trends_report.py --date 2026-02-19

入力: 今日と昨日の snapshot JSONL
出力:
  - /home/youtube-analyst-bot/vault/30_YouTubeTrends/YYYY-MM-DD.md（入口）
  - /home/youtube-analyst-bot/vault/30_YouTubeTrends/YYYY-MM-DD/<slug>.md（カテゴリ別）
"""

import argparse
import sys
from datetime import date, timedelta

from yt_common import (
    CATEGORIES,
    TRENDS_DIR,
    fmt_delta,
    fmt_number,
    hours_since,
    load_snapshot,
    now_jst,
    truncate,
)

TOP_N = 30
TITLE_MAX = 40
CHANNEL_MAX = 20


def build_rankings(today_records: list, yesterday_map: dict, now) -> dict:
    """カテゴリ別にランキングを構築する。

    Returns:
        {slug: [sorted list of record dicts with delta/vph fields]}
    """
    by_slug = {}
    for rec in today_records:
        slug = rec.get("category_slug", "unknown")
        by_slug.setdefault(slug, []).append(rec)

    rankings = {}
    for slug, records in by_slug.items():
        for rec in records:
            vid = rec["video_id"]
            views = rec.get("view_count", 0)

            yesterday_rec = yesterday_map.get(vid)
            if yesterday_rec:
                delta = views - yesterday_rec.get("view_count", 0)
                rec["delta_views"] = delta
                rec["vph"] = None
                rec["is_new"] = False
            else:
                published = rec.get("published_at", "")
                h = hours_since(published, now) if published else 1.0
                vph = views / max(1.0, h)
                rec["delta_views"] = None
                rec["vph"] = vph
                rec["is_new"] = True

        # ソート: delta_views がある動画は delta 降順、無い動画は vph 降順
        has_delta = [r for r in records if r["delta_views"] is not None]
        no_delta = [r for r in records if r["delta_views"] is None]
        has_delta.sort(key=lambda r: r["delta_views"], reverse=True)
        no_delta.sort(key=lambda r: (r["vph"] or 0), reverse=True)

        rankings[slug] = (has_delta + no_delta)[:TOP_N]

    return rankings


def render_row(rank: int, rec: dict) -> str:
    """表の1行を生成する。"""
    title = truncate(rec.get("title", ""), TITLE_MAX)
    channel = truncate(rec.get("channel_title", ""), CHANNEL_MAX)
    views = fmt_number(rec.get("view_count", 0))
    vid = rec.get("video_id", "")
    url = f"https://www.youtube.com/watch?v={vid}"

    if rec.get("is_new"):
        vph_val = rec.get("vph", 0)
        growth = f"\u2605{int(vph_val):,}/h"
    else:
        growth = fmt_delta(rec.get("delta_views", 0))

    return f"| {rank} | {title} | {channel} | {views} | {growth} | [\u25b6]({url}) |"


def render_category_md(date_str: str, cat: dict, rows: list) -> str:
    """カテゴリ別 slug.md を生成する。"""
    lines = []
    lines.append("---")
    lines.append(f"date: {date_str}")
    lines.append(f"category: {cat['name']}")
    lines.append(f"category_id: {cat['id']}")
    lines.append("type: youtube-trend-category")
    lines.append("---")
    lines.append("")
    lines.append(f"# {cat['name']} \u30c8\u30ec\u30f3\u30c9: {date_str}")
    lines.append("")
    lines.append("| # | \u30bf\u30a4\u30c8\u30eb | \u30c1\u30e3\u30f3\u30cd\u30eb | \u518d\u751f\u6570 | \u4f38\u3073 | \u30ea\u30f3\u30af |")
    lines.append("|--:|---------|-----------|-------:|-----:|:------:|")
    for i, rec in enumerate(rows, 1):
        lines.append(render_row(i, rec))
    lines.append("")
    lines.append("> \u4f38\u3073 = \u6628\u65e5\u3068\u306e\u518d\u751f\u6570\u5dee\u5206\uff08\u0394Views\uff09\u3002\u2605 = \u65b0\u898f\u52d5\u753b\uff08VPH: \u6642\u9593\u3042\u305f\u308a\u518d\u751f\u6570\u3067\u4ee3\u66ff\uff09")
    lines.append("")
    return "\n".join(lines)


def render_index_md(date_str: str, rankings: dict, total_count: int,
                    generated_ts: str) -> str:
    """入口 YYYY-MM-DD.md を生成する。"""
    lines = []
    lines.append("---")
    lines.append(f"date: {date_str}")
    lines.append("type: youtube-trend")
    lines.append("---")
    lines.append("")
    lines.append(f"# YouTube \u30c8\u30ec\u30f3\u30c9: {date_str}")
    lines.append("")
    lines.append(f"> \u81ea\u52d5\u751f\u6210: {generated_ts}")
    lines.append(f"> \u30ab\u30c6\u30b4\u30ea\u6570: {len(rankings)} / \u53d6\u5f97\u52d5\u753b\u6570: {total_count}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for cat in CATEGORIES:
        slug = cat["slug"]
        rows = rankings.get(slug, [])
        count = len(rows)
        if count == 0:
            continue

        top_title = truncate(rows[0].get("title", ""), 30) if rows else ""
        lines.append(f"<details>")
        lines.append(f"<summary>{cat['emoji']} {cat['name']}\uff08{count}\u4ef6\uff09\u2014 TOP: {top_title}</summary>")
        lines.append("")
        lines.append("| # | \u30bf\u30a4\u30c8\u30eb | \u30c1\u30e3\u30f3\u30cd\u30eb | \u518d\u751f\u6570 | \u4f38\u3073 | \u30ea\u30f3\u30af |")
        lines.append("|--:|---------|-----------|-------:|-----:|:------:|")

        for i, rec in enumerate(rows, 1):
            lines.append(render_row(i, rec))

        lines.append("")
        lines.append(f"\u2192 [\u8a73\u7d30](./{date_str}/{slug}.md)")
        lines.append("")
        lines.append("</details>")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="\u30b9\u30ca\u30c3\u30d7\u30b7\u30e7\u30c3\u30c8\u5dee\u5206\u304b\u3089 Markdown \u30ec\u30dd\u30fc\u30c8\u3092\u751f\u6210"
    )
    parser.add_argument(
        "--date",
        default=date.today().isoformat(),
        help="\u5bfe\u8c61\u65e5 YYYY-MM-DD\uff08\u7701\u7565\u6642: \u4eca\u65e5\uff09",
    )
    args = parser.parse_args()
    date_str = args.date
    yesterday_str = (date.fromisoformat(date_str) - timedelta(days=1)).isoformat()

    now = now_jst()

    # ── スナップショット読み込み ──
    today_records = load_snapshot(date_str)
    if not today_records:
        print(f"[ERROR] \u4eca\u65e5\u306e\u30b9\u30ca\u30c3\u30d7\u30b7\u30e7\u30c3\u30c8\u304c\u3042\u308a\u307e\u305b\u3093: {date_str}", file=sys.stderr)
        sys.exit(1)

    yesterday_records = load_snapshot(yesterday_str)
    yesterday_map = {r["video_id"]: r for r in yesterday_records}

    if yesterday_records:
        print(f"[INFO] \u6628\u65e5\u30c7\u30fc\u30bf\u3042\u308a: {len(yesterday_records)}\u4ef6")
    else:
        print(f"[INFO] \u6628\u65e5\u30c7\u30fc\u30bf\u306a\u3057\uff08\u5168\u52d5\u753b\u3092\u65b0\u898f\u6551\u6e08\u6307\u6a19\u3067\u4e26\u3079\u307e\u3059\uff09")

    # ── ランキング構築 ──
    rankings = build_rankings(today_records, yesterday_map, now)
    total_count = sum(len(rows) for rows in rankings.values())
    generated_ts = now.isoformat()

    # ── 入口MD ──
    index_md = render_index_md(date_str, rankings, total_count, generated_ts)
    index_path = TRENDS_DIR / f"{date_str}.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(index_md, encoding="utf-8")
    print(f"[OK] \u5165\u53e3MD: {index_path}")

    # ── カテゴリ別MD ──
    date_dir = TRENDS_DIR / date_str
    date_dir.mkdir(parents=True, exist_ok=True)

    cat_map = {c["slug"]: c for c in CATEGORIES}
    for slug, rows in rankings.items():
        cat = cat_map.get(slug)
        if not cat:
            continue
        cat_md = render_category_md(date_str, cat, rows)
        cat_path = date_dir / f"{slug}.md"
        cat_path.write_text(cat_md, encoding="utf-8")

    print(f"[OK] \u30ab\u30c6\u30b4\u30ea\u5225MD: {date_dir}/ ({len(rankings)}\u30ab\u30c6\u30b4\u30ea)")
    print(f"[DONE] \u30ec\u30dd\u30fc\u30c8\u751f\u6210\u5b8c\u4e86: {total_count}\u4ef6")


if __name__ == "__main__":
    main()
