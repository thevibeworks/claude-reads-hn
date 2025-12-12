#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.1.0
"""
Generate llms.txt from digest files.

examples:
  %(prog)s                              # regenerate full llms.txt
  %(prog)s --add digests/2025/12/X.md   # add single digest entry
  %(prog)s -n                           # dry run
"""

from __future__ import annotations

import argparse
import logging
import re
import signal
import sys
from pathlib import Path

__version__ = "0.1.0"
PROG = Path(__file__).name
LOGGER = logging.getLogger(PROG)

LLMS_TXT = Path("llms.txt")
DIGESTS_DIR = Path("digests")


def setup_logging(quiet: bool, verbose: int) -> None:
    level = logging.WARNING if quiet else logging.INFO
    level = max(logging.DEBUG, level - min(verbose, 2) * 10)
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def parse_digest(path: Path) -> dict | None:
    """Extract metadata from a digest file."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as e:
        LOGGER.warning("cannot read %s: %s", path, e)
        return None

    # Extract date/time from header: # HN Digest 2025-12-12 15:54 UTC
    header = re.search(r"# HN Digest (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", content)
    if not header:
        LOGGER.warning("no header found in %s", path)
        return None

    date, time = header.groups()

    # Extract story IDs: item?id=XXXXX
    story_ids = re.findall(r"item\?id=(\d+)", content)

    # Extract topics from Highlights section or vibe line
    topics = []
    highlights = re.search(r"\*\*Highlights\*\*\n((?:- .+\n)+)", content)
    if highlights:
        for line in highlights.group(1).strip().split("\n"):
            # "- GPT-5.2: The new hotness..." -> "GPT-5.2"
            match = re.match(r"- ([^:]+):", line)
            if match:
                topics.append(match.group(1).strip())

    if not topics:
        # Fallback: extract from vibe line
        vibe = re.search(r"^> (.+)$", content, re.MULTILINE)
        if vibe:
            topics = [vibe.group(1)[:50]]

    return {
        "path": path,
        "date": date,
        "time": time,
        "story_ids": story_ids[:5],
        "topics": topics[:5],
    }


def generate_llms_txt(digests: list[dict]) -> str:
    """Generate llms.txt content from digest metadata."""
    lines = [
        "# Claude Reads HN",
        "",
        "> AI-curated HN digests every 5 hours. Check story IDs before curating to avoid duplicates. Update after each digest.",
        "",
        "## Digests",
        "",
    ]

    # Sort by date/time descending
    digests.sort(key=lambda d: (d["date"], d["time"]), reverse=True)

    for d in digests:
        rel_path = d["path"].as_posix()
        topics_str = ", ".join(d["topics"]) if d["topics"] else "misc"
        ids_str = ", ".join(d["story_ids"]) if d["story_ids"] else ""
        line = f"- [{d['date']} {d['time']}]({rel_path}): {topics_str}"
        if ids_str:
            line += f" | {ids_str}"
        lines.append(line)

    lines.extend([
        "",
        "## Optional",
        "",
        "- Topics: AI/ML, security, programming, infrastructure, social, science",
        f"- Stats: {len(digests)} digests since 2025-12-10",
    ])

    return "\n".join(lines) + "\n"


def scan_digests() -> list[dict]:
    """Scan all digest files and extract metadata."""
    digests = []
    for md in DIGESTS_DIR.rglob("*.md"):
        d = parse_digest(md)
        if d:
            digests.append(d)
    return digests


def add_digest(path: Path) -> int:
    """Add a single digest entry to existing llms.txt."""
    if not path.exists():
        LOGGER.error("digest not found: %s", path)
        return 1

    d = parse_digest(path)
    if not d:
        return 1

    # Read existing llms.txt
    if not LLMS_TXT.exists():
        LOGGER.error("llms.txt not found, run without --add first")
        return 1

    content = LLMS_TXT.read_text(encoding="utf-8")

    # Build new entry line
    rel_path = path.as_posix()
    topics_str = ", ".join(d["topics"]) if d["topics"] else "misc"
    ids_str = ", ".join(d["story_ids"]) if d["story_ids"] else ""
    new_line = f"- [{d['date']} {d['time']}]({rel_path}): {topics_str}"
    if ids_str:
        new_line += f" | {ids_str}"

    # Insert after "## Digests\n\n"
    marker = "## Digests\n\n"
    if marker not in content:
        LOGGER.error("cannot find '## Digests' section in llms.txt")
        return 1

    pos = content.index(marker) + len(marker)
    new_content = content[:pos] + new_line + "\n" + content[pos:]

    LLMS_TXT.write_text(new_content, encoding="utf-8")
    LOGGER.info("added: %s", new_line)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog=PROG,
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-n", "--dry-run", action="store_true", help="print to stdout only")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress normal output")
    p.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
    p.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}")
    p.add_argument("--add", metavar="PATH", help="add single digest to existing llms.txt")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.quiet, args.verbose)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))

    try:
        if args.add:
            if args.dry_run:
                d = parse_digest(Path(args.add))
                if d:
                    LOGGER.info("would add: %s %s | %s", d["date"], d["time"], d["topics"])
                return 0
            return add_digest(Path(args.add))

        # Full regeneration
        digests = scan_digests()
        if not digests:
            LOGGER.error("no digests found in %s", DIGESTS_DIR)
            return 1

        content = generate_llms_txt(digests)

        if args.dry_run:
            print(content)
        else:
            LLMS_TXT.write_text(content, encoding="utf-8")
            LOGGER.info("wrote %s (%d digests)", LLMS_TXT, len(digests))

        return 0

    except Exception as e:
        LOGGER.error("error: %s", e)
        if args.verbose:
            raise
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
