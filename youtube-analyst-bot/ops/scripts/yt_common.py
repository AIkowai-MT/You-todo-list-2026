#!/usr/bin/env python3
"""yt_common.py - YouTube トレンドリサーチ共通関数.

標準ライブラリのみ使用。
"""

import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── パス定数 ─────────────────────────────────────────────
OPS_DIR = Path("/home/youtube-analyst-bot/ops")
SNAPSHOT_DIR = OPS_DIR / "data" / "youtube" / "snapshots"
VAULT_DIR = Path("/home/youtube-analyst-bot/vault")
TRENDS_DIR = VAULT_DIR / "30_YouTubeTrends"
API_KEY_FILE = Path("/home/youtube-analyst-bot/.config/youtube_api_key")

# ── allowlist（15カテゴリ固定） ───────────────────────────
CATEGORIES = [
    {"id": "10", "name": "Music",                 "slug": "music",                "emoji": "\U0001f3b5"},
    {"id": "20", "name": "Gaming",                "slug": "gaming",               "emoji": "\U0001f3ae"},
    {"id": "24", "name": "Entertainment",          "slug": "entertainment",        "emoji": "\U0001f3ac"},
    {"id": "23", "name": "Comedy",                 "slug": "comedy",               "emoji": "\U0001f923"},
    {"id": "22", "name": "People & Blogs",         "slug": "people_blogs",         "emoji": "\U0001f465"},
    {"id": "25", "name": "News & Politics",        "slug": "news_politics",        "emoji": "\U0001f4f0"},
    {"id": "17", "name": "Sports",                 "slug": "sports",               "emoji": "\u26bd"},
    {"id": "26", "name": "Howto & Style",          "slug": "howto_style",          "emoji": "\U0001f4a1"},
    {"id": "27", "name": "Education",              "slug": "education",            "emoji": "\U0001f393"},
    {"id": "28", "name": "Science & Technology",   "slug": "science_technology",   "emoji": "\U0001f52c"},
    {"id": "1",  "name": "Film & Animation",       "slug": "film_animation",       "emoji": "\U0001f3a5"},
    {"id": "2",  "name": "Autos & Vehicles",       "slug": "autos_vehicles",       "emoji": "\U0001f697"},
    {"id": "15", "name": "Pets & Animals",         "slug": "pets_animals",         "emoji": "\U0001f43e"},
    {"id": "19", "name": "Travel & Events",        "slug": "travel_events",        "emoji": "\u2708\ufe0f"},
    {"id": "29", "name": "Nonprofits & Activism",  "slug": "nonprofits_activism",  "emoji": "\U0001f91d"},
]


# ── API Key ──────────────────────────────────────────────
def load_api_key() -> str:
    """API Key をファイルから読み取る（1行テキスト）。"""
    return API_KEY_FILE.read_text(encoding="utf-8").strip()


# ── YouTube API 呼び出し ─────────────────────────────────
def fetch_most_popular(api_key: str, category_id: str,
                       region_code: str = "JP",
                       max_results: int = 50) -> list:
    """videos.list (chart=mostPopular) を呼び出し、items を返す。

    APIエラー時はそのカテゴリをスキップ（空リスト返却＋stderr警告）。
    """
    params = (
        f"part=id,snippet,statistics"
        f"&chart=mostPopular"
        f"&regionCode={region_code}"
        f"&videoCategoryId={category_id}"
        f"&maxResults={max_results}"
        f"&fields=items(id,snippet(publishedAt,title,channelTitle,channelId),"
        f"statistics(viewCount,likeCount,commentCount))"
        f"&key={api_key}"
    )
    url = f"https://www.googleapis.com/youtube/v3/videos?{params}"

    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("items", [])
    except urllib.error.HTTPError as e:
        import sys
        print(f"[WARN] API HTTPError category={category_id}: {e.code} {e.reason}",
              file=sys.stderr)
        return []
    except urllib.error.URLError as e:
        import sys
        print(f"[WARN] API URLError category={category_id}: {e.reason}",
              file=sys.stderr)
        return []
    except Exception as e:
        import sys
        print(f"[WARN] API Error category={category_id}: {e}",
              file=sys.stderr)
        return []


# ── JSONL 読み書き ───────────────────────────────────────
def save_snapshot(records: list, date_str: str) -> Path:
    """レコードをJSONLとして保存する。"""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{date_str}.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return path


def load_snapshot(date_str: str) -> list:
    """指定日のJSONLスナップショットを読み込む。無ければ空リスト。"""
    path = SNAPSHOT_DIR / f"{date_str}.jsonl"
    if not path.exists():
        return []
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


# ── 数値フォーマット ─────────────────────────────────────
def fmt_number(n: int) -> str:
    """数値をカンマ区切りで返す。"""
    return f"{n:,}"


def fmt_delta(n: int) -> str:
    """差分を +N / -N 形式で返す。"""
    if n >= 0:
        return f"+{n:,}"
    return f"{n:,}"


def truncate(text: str, max_len: int) -> str:
    """文字列を max_len 文字で切り詰める。"""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "\u2026"


# ── 時刻ユーティリティ ───────────────────────────────────
def parse_iso(dt_str: str) -> datetime:
    """ISO 8601 文字列を datetime に変換する。"""
    # Python 3.7+ の fromisoformat は 'Z' を直接扱えない
    dt_str = dt_str.replace("Z", "+00:00")
    return datetime.fromisoformat(dt_str)


def hours_since(dt_str: str, now: datetime) -> float:
    """公開日時から now までの経過時間（時間単位）を返す。"""
    published = parse_iso(dt_str)
    delta = now - published
    return max(delta.total_seconds() / 3600.0, 0.0)


def now_jst() -> datetime:
    """現在時刻（UTC aware）を返す。"""
    return datetime.now(timezone.utc)
