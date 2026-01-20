#!/usr/bin/env python3
import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime


def fetch_rss(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read()


def text_or_empty(elem):
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def extract_thumbnail(content_html):
    if not content_html:
        return ""
    match = re.search(r'<img[^>]+src="([^">]+)"', content_html)
    return match.group(1) if match else ""


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


def parse_rss(xml_bytes):
    root = ET.fromstring(xml_bytes)
    ns = {
        "content": "http://purl.org/rss/1.0/modules/content/",
        "media": "http://search.yahoo.com/mrss/",
        "atom": "http://www.w3.org/2005/Atom",
    }

    items = []
    for item in root.findall(".//item"):
        title = text_or_empty(item.find("title"))
        link = text_or_empty(item.find("link"))
        pub_date_raw = text_or_empty(item.find("pubDate"))
        pub_date = format_date(pub_date_raw)
        content = text_or_empty(item.find("content:encoded", ns)) or text_or_empty(
            item.find("description")
        )
        thumbnail = ""
        media_thumb = item.find("media:thumbnail", ns)
        if media_thumb is not None:
            thumbnail = media_thumb.attrib.get("url", "")
        if not thumbnail:
            media_content = item.find("media:content", ns)
            if media_content is not None:
                thumbnail = media_content.attrib.get("url", "")
        if not thumbnail:
            enclosure = item.find("enclosure")
            if enclosure is not None:
                thumbnail = enclosure.attrib.get("url", "")
        if not thumbnail:
            thumbnail = extract_thumbnail(content)

        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "pubDateRaw": iso_date(pub_date_raw),
                "thumbnail": thumbnail,
                "source": "Medium",
            }
        )

    if items:
        return items

    for entry in root.findall(".//atom:entry", ns):
        title = text_or_empty(entry.find("atom:title", ns))
        link_el = entry.find("atom:link", ns)
        link = link_el.attrib.get("href", "").strip() if link_el is not None else ""
        pub_date_raw = text_or_empty(entry.find("atom:updated", ns))
        pub_date = format_date(pub_date_raw)
        content = text_or_empty(entry.find("atom:content", ns)) or text_or_empty(
            entry.find("atom:summary", ns)
        )
        thumbnail = extract_thumbnail(content)

        if not title or not link:
            continue

        items.append(
            {
                "title": title,
                "link": link,
                "pubDate": pub_date,
                "pubDateRaw": iso_date(pub_date_raw),
                "thumbnail": thumbnail,
                "source": "Medium",
            }
        )

    return items


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_devto(username):
    url = f"https://dev.to/api/articles?username={username}"
    data = fetch_json(url)
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
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--devto-username", required=False)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rss_url = f"https://medium.com/feed/@{args.username}"
    xml_bytes = fetch_rss(rss_url)
    items = parse_rss(xml_bytes)

    if args.devto_username:
        items.extend(fetch_devto(args.devto_username))

    items.sort(key=lambda item: item.get("pubDateRaw", ""), reverse=True)

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"items": items}, f, ensure_ascii=True, indent=2)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Failed to fetch Medium feed: {exc}", file=sys.stderr)
        sys.exit(1)
