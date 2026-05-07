#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.request
from datetime import datetime
from email.utils import parsedate_to_datetime


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_datetime(raw):
    if not raw:
        return None
    try:
        return parsedate_to_datetime(raw)
    except Exception:
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            return None


def format_date(raw):
    dt = parse_datetime(raw)
    if not dt:
        return raw or ""
    return dt.strftime("%b %d, %Y")


def iso_date(raw):
    dt = parse_datetime(raw)
    if not dt:
        return ""
    return dt.isoformat()


def build_items(data):
    items = []
    for item in data:
        pub_date_raw = item.get("published_at", "")
        items.append(
            {
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "pubDate": format_date(pub_date_raw),
                "pubDateRaw": iso_date(pub_date_raw),
                "thumbnail": item.get("cover_image") or item.get("social_image") or "",
                "source": "Dev.to",
            }
        )
    items.sort(key=lambda item: item.get("pubDateRaw", ""), reverse=True)
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        url = f"https://dev.to/api/articles?username={args.username}"
        data = fetch_json(url)
        if not isinstance(data, list):
            raise ValueError(f"Expected list from Dev.to API, got {type(data).__name__}")
        items = build_items(data)

        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=True, indent=2)

        print(f"Dev.to articles: {len(items)}")
    except Exception as exc:
        print(f"Failed to fetch Dev.to articles: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
