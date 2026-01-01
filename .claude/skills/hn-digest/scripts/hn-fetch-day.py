#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""
Fetch historical HN stories for a single day, formatted for digest curation.

Output format matches /tmp/hn/stories.md expected by the digest skill.

examples:
  %(prog)s 2025-06-15                        # Fetch June 15, 2025
  %(prog)s 2025-06-15 -o /tmp/hn/stories.md  # Save for digest workflow
  %(prog)s 2025-06-15 -n 30 -p 50            # More stories, lower threshold
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
import httpx

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def fetch_day(date: datetime, limit: int = 20, min_points: int = 100) -> list:
    """Fetch top stories for a single day from Algolia."""
    start = datetime(date.year, date.month, date.day)
    end = start + timedelta(days=1)

    filters = [
        f"created_at_i>{int(start.timestamp())}",
        f"created_at_i<{int(end.timestamp())}",
        f"points>{min_points}",
    ]
    params = {
        "tags": "story",
        "numericFilters": json.dumps(filters),
        "hitsPerPage": limit,
    }

    resp = httpx.get(ALGOLIA_URL, params=params, timeout=30)
    resp.raise_for_status()

    stories = [
        {
            "id": h.get("objectID"),
            "title": h.get("title"),
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "points": h.get("points", 0),
            "comments": h.get("num_comments", 0),
            "author": h.get("author"),
            "created_at": h.get("created_at"),
        }
        for h in resp.json().get("hits", [])
    ]
    return sorted(stories, key=lambda s: s["points"], reverse=True)


def to_markdown(stories: list, date: datetime) -> str:
    """Format stories as markdown matching digest skill input format."""
    lines = [
        f"# HN Top Stories - {date.strftime('%Y-%m-%d')}",
        "",
        f"Fetched from Algolia historical archive.",
        f"Stories with 100+ points from {date.strftime('%B %d, %Y')}.",
        "",
        "---",
        "",
    ]

    for i, s in enumerate(stories, 1):
        hn_url = f"https://news.ycombinator.com/item?id={s['id']}"
        lines.extend([
            f"## {i}. {s['title']}",
            "",
            f"- **URL**: {s['url']}",
            f"- **HN**: {hn_url}",
            f"- **Points**: {s['points']}",
            f"- **Comments**: {s['comments']}",
            f"- **Author**: {s['author']}",
            f"- **Posted**: {s['created_at']}",
            "",
            "---",
            "",
        ])

    return "\n".join(lines)


def to_json(stories: list, date: datetime) -> str:
    """Format as JSON for programmatic use."""
    return json.dumps({
        "date": date.strftime("%Y-%m-%d"),
        "source": "algolia",
        "stories": stories,
    }, indent=2)


def main():
    p = argparse.ArgumentParser(
        description="Fetch historical HN stories for digest curation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("date", help="Date to fetch (YYYY-MM-DD)")
    p.add_argument("-n", "--limit", type=int, default=20, help="Max stories (default: 20)")
    p.add_argument("-p", "--min-points", type=int, default=100, help="Min points (default: 100)")
    p.add_argument("-o", "--output", help="Output file (.md or .json)")
    p.add_argument("--json", action="store_true", help="Force JSON output")
    args = p.parse_args()

    date = datetime.strptime(args.date, "%Y-%m-%d")
    stories = fetch_day(date, args.limit, args.min_points)

    print(f"Fetched {len(stories)} stories for {date.strftime('%Y-%m-%d')}", file=sys.stderr)

    if args.json or (args.output and args.output.endswith(".json")):
        content = to_json(stories, date)
    else:
        content = to_markdown(stories, date)

    if args.output:
        from pathlib import Path
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(content)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(content)


if __name__ == "__main__":
    main()
