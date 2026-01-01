#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///
"""
Fetch historical HN front page stories from Algolia.

examples:
  %(prog)s 2025-W01                          # Week 1 of 2025
  %(prog)s 2025-W01 2025-W04                 # Weeks 1-4
  %(prog)s 2025-W01 -q "LLM AI Claude"       # Week 1, AI-related only
  %(prog)s 2025-W01 2025-W52 -q "Claude" -o claude-2025.json
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
import httpx

ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def week_range(iso_week: str) -> tuple[datetime, datetime]:
    """Parse ISO week (2025-W01) to (monday, next_monday)."""
    year, week = iso_week.split("-W")
    # ISO 8601: %G=year, %V=week, %u=weekday (1=Monday)
    monday = datetime.strptime(f"{year}-{week}-1", "%G-%V-%u")
    return monday, monday + timedelta(days=7)


def fetch_week(start: datetime, end: datetime, query: str = "", limit: int = 15, min_points: int = 100) -> list:
    """Fetch top stories for a week from Algolia."""
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
    if query:
        params["query"] = query

    resp = httpx.get(ALGOLIA_URL, params=params, timeout=30)
    resp.raise_for_status()

    stories = [
        {
            "id": h.get("objectID"),
            "title": h.get("title"),
            "url": h.get("url"),
            "points": h.get("points", 0),
            "comments": h.get("num_comments", 0),
            "author": h.get("author"),
            "date": h.get("created_at"),
            "hn_url": f"https://news.ycombinator.com/item?id={h.get('objectID')}",
        }
        for h in resp.json().get("hits", [])
    ]
    return sorted(stories, key=lambda s: s["points"], reverse=True)


def week_label(iso_week: str) -> str:
    """2025-W01 -> 'W01 (Dec 30 - Jan 5)'"""
    start, end = week_range(iso_week)
    return f"{iso_week} ({start.strftime('%b %d')} - {(end - timedelta(days=1)).strftime('%b %d')})"


def iter_weeks(start_week: str, end_week: str):
    """Yield ISO week strings from start to end inclusive."""
    start, _ = week_range(start_week)
    end, _ = week_range(end_week)
    current = start
    while current <= end:
        yield current.strftime("%G-W%V")
        current += timedelta(days=7)


def to_markdown(weeks_data: list, query: str) -> str:
    """Render weeks data as markdown."""
    lines = ["# HN History\n"]
    if query:
        lines.append(f"**Filter:** {query}\n")
    lines.append("")

    for week in weeks_data:
        lines.append(f"## {week['label']}\n")
        for i, s in enumerate(week["stories"], 1):
            lines.append(f"{i}. [{s['title']}]({s['url'] or s['hn_url']}) - {s['points']}pts, {s['comments']}c")
        lines.append("")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(
        description="Fetch historical HN stories by week",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("start_week", help="Start week (2025-W01)")
    p.add_argument("end_week", nargs="?", help="End week (default: same as start)")
    p.add_argument("-q", "--query", default="", help="Search filter (e.g., 'LLM AI')")
    p.add_argument("-n", "--limit", type=int, default=15, help="Stories per week (default: 15)")
    p.add_argument("-p", "--min-points", type=int, default=100, help="Minimum points (default: 100)")
    p.add_argument("-o", "--output", help="Output file (.json or .md)")
    p.add_argument("--json", action="store_true", help="Force JSON output")
    args = p.parse_args()

    end_week = args.end_week or args.start_week
    weeks_data = []

    for iso_week in iter_weeks(args.start_week, end_week):
        start, end = week_range(iso_week)
        stories = fetch_week(start, end, args.query, args.limit, args.min_points)
        weeks_data.append({
            "week": iso_week,
            "label": week_label(iso_week),
            "start": start.isoformat(),
            "end": end.isoformat(),
            "stories": stories,
        })
        print(f"Fetched {iso_week}: {len(stories)} stories", file=sys.stderr)

    # Output
    if args.output:
        is_md = args.output.endswith(".md") and not args.json
        content = to_markdown(weeks_data, args.query) if is_md else json.dumps(weeks_data, indent=2)
        with open(args.output, "w") as f:
            f.write(content)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        if args.json:
            print(json.dumps(weeks_data, indent=2))
        else:
            print(to_markdown(weeks_data, args.query))


if __name__ == "__main__":
    main()
