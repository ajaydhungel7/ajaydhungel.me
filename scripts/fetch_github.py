#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.request
from datetime import datetime


def fetch_json(url):
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/vnd.github+json"}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_date(raw):
    if not raw:
        return ""
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y")
    except Exception:
        return raw


def iso_date(raw):
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).isoformat()
    except Exception:
        return raw


def build_items(repos, limit, pinned):
    items = []
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        name = repo.get("name", "")
        items.append(
            {
                "name": name,
                "description": repo.get("description") or "",
                "url": repo.get("html_url", ""),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "language": repo.get("language") or "",
                "topics": repo.get("topics", []),
                "updatedAt": format_date(repo.get("updated_at", "")),
                "updatedAtRaw": iso_date(repo.get("updated_at", "")),
                "pinned": name in pinned,
            }
        )

    # Pinned repos first (in declared order), then by stars descending
    pin_order = {name: i for i, name in enumerate(pinned)}
    items.sort(key=lambda r: (
        pin_order.get(r["name"], len(pinned) + 1),
        -r["stars"],
    ))
    return items[:limit]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--pin", nargs="*", default=[], metavar="REPO",
                        help="Repo names to pin at the top, in order")
    args = parser.parse_args()

    try:
        url = f"https://api.github.com/users/{args.user}/repos?sort=updated&per_page=100&type=owner"
        repos = fetch_json(url)
        if not isinstance(repos, list):
            raise ValueError(f"Expected list from GitHub API, got {type(repos).__name__}")
        items = build_items(repos, args.limit, pinned=args.pin)

        with open(args.out, "w", encoding="utf-8") as f:
            json.dump({"items": items}, f, ensure_ascii=True, indent=2)

        print(f"GitHub projects: {len(items)}")
    except Exception as exc:
        print(f"Failed to fetch GitHub projects: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
