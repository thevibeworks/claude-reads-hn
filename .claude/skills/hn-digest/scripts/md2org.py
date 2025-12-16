#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.1.0
"""
Convert markdown HN digests to org-mode format.

examples:
  %(prog)s digests/2025/12/15-1100.md             # convert single file
  %(prog)s digests/2025/12/*.md                   # convert all in directory
  %(prog)s digests/2025/12/*.md --delete          # convert and remove md files
"""

import argparse
import logging
import re
import signal
import sys
from pathlib import Path

__version__ = "0.1.0"
PROG = Path(__file__).name
LOGGER = logging.getLogger(PROG)


def setup_logging(quiet: bool, verbose: int) -> None:
    level = logging.WARNING if quiet else logging.INFO
    level = max(logging.DEBUG, level - min(verbose, 2) * 10)
    logging.basicConfig(level=level, format="%(levelname)s %(message)s")


def parse_md_digest(content: str) -> dict:
    """Parse markdown digest into structured data."""
    result = {
        "date": "",
        "vibe": "",
        "highlights": [],
        "stories": []
    }

    lines = content.split("\n")
    i = 0

    # Parse header: # HN Digest 2025-12-15 11:00 UTC
    while i < len(lines):
        line = lines[i]
        if line.startswith("# HN Digest"):
            match = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2})", line)
            if match:
                result["date"] = f"{match.group(1)}T{match.group(2)}:00Z"
            i += 1
            break
        i += 1

    # Parse vibe: > one-liner (skip i18n comments)
    while i < len(lines):
        line = lines[i]
        if line.startswith("> "):
            result["vibe"] = line[2:].strip()
            i += 1
            break
        elif line.startswith("<!--"):
            i += 1
            continue
        elif line.strip():
            i += 1
        else:
            i += 1

    # Skip i18n vibe translations
    while i < len(lines) and (lines[i].startswith("<!--") or not lines[i].strip()):
        i += 1

    # Parse highlights
    if i < len(lines) and "**Highlights**" in lines[i]:
        i += 1
        while i < len(lines):
            line = lines[i]
            if line.startswith("- ") and not line.startswith("<!-- i18n"):
                result["highlights"].append(line[2:].strip())
            elif line.startswith("---"):
                break
            elif line.startswith("###"):
                break
            i += 1

    # Parse stories
    current_story = None
    while i < len(lines):
        line = lines[i]

        # Story title: ### [Title](url) • Xpts Yc
        story_match = re.match(r"### \[(.+?)\]\((.+?)\) • (\d+)pts (\d+)c", line)
        if story_match:
            if current_story:
                result["stories"].append(current_story)

            current_story = {
                "title": story_match.group(1),
                "url": story_match.group(2),
                "points": int(story_match.group(3)),
                "comments_count": int(story_match.group(4)),
                "hn_url": "",
                "id": 0,
                "tldr": "",
                "take": "",
                "tags": [],
                "comments": [],
                "i18n": {}
            }
            i += 1
            continue

        # HN discussion link
        hn_match = re.search(r"\[HN discussion\]\((https://news\.ycombinator\.com/item\?id=(\d+))\)", line)
        if hn_match and current_story:
            current_story["hn_url"] = hn_match.group(1)
            current_story["id"] = int(hn_match.group(2))
            i += 1
            continue

        # TLDR (skip i18n versions)
        if line.startswith("TLDR:") and current_story:
            current_story["tldr"] = line[5:].strip()
            i += 1
            # Capture i18n TLDRs
            while i < len(lines) and lines[i].startswith("<!-- i18n:"):
                i18n_match = re.match(r"<!-- i18n:(\w+) -->TLDR: (.+?)<!-- /i18n -->", lines[i])
                if i18n_match:
                    lang = i18n_match.group(1)
                    if lang not in current_story["i18n"]:
                        current_story["i18n"][lang] = {}
                    current_story["i18n"][lang]["tldr"] = i18n_match.group(2)
                i += 1
            continue

        # Take (skip i18n versions)
        if line.startswith("Take:") and current_story:
            current_story["take"] = line[5:].strip()
            i += 1
            # Capture i18n Takes
            while i < len(lines) and lines[i].startswith("<!-- i18n:"):
                i18n_match = re.match(r"<!-- i18n:(\w+) -->Take: (.+?)<!-- /i18n -->", lines[i])
                if i18n_match:
                    lang = i18n_match.group(1)
                    if lang not in current_story["i18n"]:
                        current_story["i18n"][lang] = {}
                    current_story["i18n"][lang]["take"] = i18n_match.group(2)
                i += 1
            continue

        # Comments
        if line.startswith("Comments:") and current_story:
            i += 1
            while i < len(lines):
                cline = lines[i]
                # Comment: - "text" -username
                comment_match = re.match(r'- ["\'](.+?)["\']\s*-(\w+)', cline)
                if comment_match:
                    current_story["comments"].append({
                        "text": comment_match.group(1),
                        "by": comment_match.group(2),
                        "id": 0
                    })
                elif cline.startswith("<!-- i18n"):
                    pass  # skip i18n comment translations
                elif cline.startswith("Tags:") or cline.startswith("---") or cline.startswith("###"):
                    break
                i += 1
            continue

        # Tags
        if line.startswith("Tags:") and current_story:
            tags = re.findall(r"#(\w+)", line)
            current_story["tags"] = tags
            i += 1
            continue

        # End of story section
        if line.startswith("---"):
            if current_story:
                result["stories"].append(current_story)
                current_story = None
            i += 1
            continue

        i += 1

    if current_story:
        result["stories"].append(current_story)

    return result


def escape_org(text: str) -> str:
    """Escape special org-mode characters."""
    if not text:
        return ""
    return text.replace("*", "⁎").replace("[", "［").replace("]", "］")


def format_tags(tags: list) -> str:
    """Format tags as org-mode tag string."""
    if not tags:
        return ""
    clean_tags = [t.lstrip('#').lower() for t in tags]
    return ":" + ":".join(clean_tags) + ":"


def digest_to_org(digest: dict) -> str:
    """Convert parsed digest to org format."""
    date = digest.get("date", "")
    if "T" in date:
        date_display = date.replace("T", " ").replace("Z", " UTC")[:22] + " UTC"
    else:
        date_display = date + " UTC"

    org = f"""#+TITLE: HN Digest {date_display}
#+DATE: {date}
#+CURATOR: claude
#+SOURCE: https://hacker-news.firebaseio.com/v0/

* Vibe
{escape_org(digest.get('vibe', ''))}

"""

    highlights = digest.get("highlights", [])
    if highlights:
        org += "* Highlights\n"
        for h in highlights:
            org += f"- {escape_org(h)}\n"
        org += "\n"

    org += "* Stories\n"

    for story in digest.get("stories", []):
        title = escape_org(story.get("title", "Untitled"))
        tags = format_tags(story.get("tags", []))
        story_id = story.get("id", 0)
        url = story.get("url", "")
        hn_url = story.get("hn_url", f"https://news.ycombinator.com/item?id={story_id}")
        points = story.get("points", 0)
        comments_count = story.get("comments_count", 0)

        org += f"""
** {title} {tags}
:PROPERTIES:
:ID:       {story_id}
:URL:      {url}
:HN_URL:   {hn_url}
:POINTS:   {points}
:COMMENTS: {comments_count}
:END:
"""

        if story.get("tldr"):
            org += f"""
*** TLDR
{escape_org(story['tldr'])}
"""

        if story.get("take"):
            org += f"""
*** Take
{escape_org(story['take'])}
"""

        comments = story.get("comments", [])
        if comments:
            org += "\n*** Comments\n"
            for c in comments:
                author = c.get("by", "anon")
                text = escape_org(c.get("text", ""))
                comment_id = c.get("id", 0)
                org += f"""
**** {author}
:PROPERTIES:
:COMMENT_ID: {comment_id}
:END:
{text}
"""

        i18n = story.get("i18n", {})
        if i18n:
            org += f"\n*** i18n{' ' * 50}:i18n:\n"
            for lang, data in i18n.items():
                org += f"""
**** {lang}
:PROPERTIES:
:LANG: {lang}
:END:"""
                if data.get("tldr"):
                    org += f"""
***** TLDR
{escape_org(data['tldr'])}"""
                if data.get("take"):
                    org += f"""
***** Take
{escape_org(data['take'])}"""

    return org


def convert_file(md_path: Path, delete: bool = False, dry_run: bool = False) -> bool:
    """Convert a single markdown file to org."""
    org_path = md_path.with_suffix(".org")

    if dry_run:
        LOGGER.info("DRY-RUN: %s -> %s", md_path, org_path)
        return True

    try:
        content = md_path.read_text(encoding="utf-8")
        digest = parse_md_digest(content)

        if not digest["date"]:
            LOGGER.warning("no date found in %s, skipping", md_path)
            return False

        org_content = digest_to_org(digest)
        org_path.write_text(org_content, encoding="utf-8")
        LOGGER.info("converted: %s -> %s", md_path, org_path)

        if delete:
            md_path.unlink()
            LOGGER.info("deleted: %s", md_path)

        return True

    except Exception as e:
        LOGGER.error("failed to convert %s: %s", md_path, e)
        return False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog=PROG,
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("-n", "--dry-run", action="store_true", help="print actions only")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress normal output")
    p.add_argument("-v", "--verbose", action="count", default=0, help="increase verbosity")
    p.add_argument("-V", "--version", action="version", version=f"{PROG} {__version__}")
    p.add_argument("--delete", action="store_true", help="delete md files after conversion")
    p.add_argument("files", nargs="+", help="markdown files to convert")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.quiet, args.verbose)
    signal.signal(signal.SIGINT, lambda *_: sys.exit(130))

    success = 0
    failed = 0

    for f in args.files:
        path = Path(f)
        if not path.exists():
            LOGGER.warning("file not found: %s", path)
            failed += 1
            continue

        if path.suffix != ".md":
            LOGGER.warning("not a markdown file: %s", path)
            failed += 1
            continue

        if convert_file(path, delete=args.delete, dry_run=args.dry_run):
            success += 1
        else:
            failed += 1

    LOGGER.info("converted %d files, %d failed", success, failed)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
