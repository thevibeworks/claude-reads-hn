#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.1.0
"""
Convert curated HN digest JSON to org-mode format.

examples:
  %(prog)s input.json output.org
  %(prog)s input.json  # stdout
"""

import json
import sys
from datetime import datetime
from pathlib import Path


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


def comment_to_org(comment: dict, level: int = 4) -> str:
    """Convert a comment to org format."""
    stars = "*" * level
    author = comment.get("by", comment.get("author", "anon"))
    text = escape_org(comment.get("text", ""))
    comment_id = comment.get("id", comment.get("comment_id", ""))

    props = ""
    if comment_id:
        props = f"""
:PROPERTIES:
:COMMENT_ID: {comment_id}
:END:"""

    return f"""
{stars} {author}{props}
{text}
"""


def i18n_to_org(lang: str, data: dict, level: int = 4) -> str:
    """Convert i18n translation to org format."""
    stars = "*" * level
    sub_stars = "*" * (level + 1)

    parts = [f"""
{stars} {lang}
:PROPERTIES:
:LANG: {lang}
:END:"""]

    if data.get("tldr"):
        parts.append(f"""
{sub_stars} TLDR
{escape_org(data['tldr'])}""")

    if data.get("take"):
        parts.append(f"""
{sub_stars} Take
{escape_org(data['take'])}""")

    return "".join(parts)


def story_to_org(story: dict, level: int = 2) -> str:
    """Convert a story to org format."""
    stars = "*" * level
    sub_stars = "*" * (level + 1)

    title = escape_org(story.get("title", "Untitled"))
    tags = format_tags(story.get("tags", []))

    story_id = story.get("id", story.get("hn_id", ""))
    url = story.get("url", "")
    hn_url = story.get("hn_url", f"https://news.ycombinator.com/item?id={story_id}")
    points = story.get("points", story.get("score", 0))
    comments_count = story.get("comments_count", story.get("descendants", 0))
    by = story.get("by", story.get("author", ""))
    time = story.get("time", "")

    if isinstance(time, int):
        time = datetime.utcfromtimestamp(time).isoformat() + "Z"

    props = f""":PROPERTIES:
:ID:       {story_id}
:URL:      {url}
:HN_URL:   {hn_url}
:POINTS:   {points}
:COMMENTS: {comments_count}"""

    if by:
        props += f"\n:BY:       {by}"
    if time:
        props += f"\n:TIME:     {time}"

    props += "\n:END:"

    org = f"""
{stars} {title} {tags}
{props}
"""

    if story.get("tldr"):
        org += f"""
{sub_stars} TLDR
{escape_org(story['tldr'])}
"""

    if story.get("take"):
        org += f"""
{sub_stars} Take
{escape_org(story['take'])}
"""

    comments = story.get("comments", [])
    if comments:
        org += f"\n{sub_stars} Comments\n"
        for c in comments:
            org += comment_to_org(c, level + 2)

    i18n = story.get("i18n", {})
    if i18n:
        org += f"\n{sub_stars} i18n{' ' * 50}:i18n:\n"
        for lang, data in i18n.items():
            org += i18n_to_org(lang, data, level + 2)

    return org


def digest_to_org(digest: dict) -> str:
    """Convert full digest JSON to org format."""
    date = digest.get("date", datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"))

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
        org += story_to_org(story)

    return org


def main():
    if len(sys.argv) < 2:
        print("Usage: json2org.py input.json [output.org]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    with open(input_path) as f:
        data = json.load(f)

    if "digest" in data:
        data = data["digest"]

    org_content = digest_to_org(data)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(org_content)
        print(f"Wrote {output_path}", file=sys.stderr)
    else:
        print(org_content)


if __name__ == "__main__":
    main()
