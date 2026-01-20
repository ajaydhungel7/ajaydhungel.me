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
    for badge in data.get("data", []):
        if not badge.get("public") or badge.get("state") != "accepted":
            continue
        template = badge.get("badge_template", {})
        badge_id = badge.get("id", "")
        issued_at_raw = badge.get("issued_at", "")
        expires_at_raw = badge.get("expires_at", "")

        items.append(
            {
                "title": template.get("name", ""),
                "link": f"https://www.credly.com/badges/{badge_id}",
                "issuedAt": format_date(issued_at_raw),
                "issuedAtRaw": iso_date(issued_at_raw),
                "expiresAt": format_date(expires_at_raw),
                "thumbnail": template.get("image_url", "") or badge.get("image_url", ""),
                "source": "Credly",
            }
        )
    items.sort(key=lambda item: item.get("issuedAtRaw", ""), reverse=True)
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    url = f"https://www.credly.com/users/{args.user}/badges.json"
    data = fetch_json(url)
    items = build_items(data)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=True, indent=2)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to fetch Credly badges: {exc}", file=sys.stderr)
        sys.exit(1)
