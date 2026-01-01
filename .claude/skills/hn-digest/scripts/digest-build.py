#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Build HTML/org/llms.txt from digest JSON files.

Replaces: json2org.py + org2html.py chain
Source of truth: JSON files in digests/

examples:
  %(prog)s digests/**/*.json -o index.html              # All digests → HTML
  %(prog)s digests/**/*.json -o index.html -d 7         # Last 7 days
  %(prog)s digests/**/*.json -o index.html -d 7 -a archive.html
  %(prog)s digests/2025/12/27-1100.json --format org    # Single → org
  %(prog)s digests/**/*.json --format llms -o llms.txt  # Generate memory index
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from string import Template

SCRIPT_DIR = Path(__file__).parent
TEMPLATE_PATH = SCRIPT_DIR / "template.html"


def story_anchor(story_id: int, digest_date: str) -> str:
    """Generate unique story anchor: s{id}-{MMDDHHMM}"""
    if not story_id or story_id <= 0:
        return ""
    suffix = ""
    if digest_date and len(digest_date) >= 16:
        try:
            month = digest_date[5:7]
            day = digest_date[8:10]
            hour = digest_date[11:13]
            minute = digest_date[14:16]
            suffix = f"-{month}{day}{hour}{minute}"
        except (IndexError, ValueError):
            pass
    return f"s{story_id}{suffix}"


def load_template() -> Template:
    """Load HTML template."""
    return Template(TEMPLATE_PATH.read_text(encoding="utf-8"))


def story_to_html(story: dict, digest_date: str = "") -> str:
    """Render a story to HTML."""
    story_id = story.get("id")
    anchor = story_anchor(story_id, digest_date)
    title = escape(story.get("title", ""))
    url = escape(story.get("url", ""))
    hn_url = escape(story.get("hn_url", ""))
    points = story.get("points", 0)
    comments_count = story.get("comments_count", 0)

    content = story.get("content", {})
    tldr = escape(content.get("tldr", ""))
    take = escape(content.get("take", ""))

    i18n = story.get("i18n", {})

    # Title translations
    title_i18n = "".join(
        f'<div class="i18n-title" data-lang="{lang}">{escape(data.get("title", ""))}</div>\n'
        for lang, data in i18n.items() if data.get("title")
    )

    # TLDR translations
    tldr_i18n = "".join(
        f'<span class="i18n-text" data-lang="{lang}">{escape(data.get("tldr", ""))}</span>\n'
        for lang, data in i18n.items() if data.get("tldr")
    )

    # Take translations
    take_i18n = "".join(
        f'<span class="i18n-text" data-lang="{lang}">{escape(data.get("take", ""))}</span>\n'
        for lang, data in i18n.items() if data.get("take")
    )

    # Tags
    tags_html = "".join(
        f'<span class="tag">#{escape(tag)}</span>'
        for tag in story.get("tags", [])
    )

    # Comments
    comments = content.get("comments", [])
    comments_parts = []
    for idx, c in enumerate(comments):
        comment_text = escape(c.get("text", ""))
        comment_author = escape(c.get("by", ""))
        comment_i18n = "".join(
            f'<div class="comment-i18n" data-lang="{lang}">{escape(data.get("comments", [])[idx] if idx < len(data.get("comments", [])) else "")}</div>\n'
            for lang, data in i18n.items()
            if data.get("comments") and idx < len(data["comments"]) and data["comments"][idx]
        )
        comments_parts.append(f'''<div class="comment">
          <div class="comment-text">"{comment_text}"</div>
          {comment_i18n}
          <div class="comment-author">-- {comment_author}</div>
        </div>''')

    comments_html = "".join(comments_parts)

    # Build sections
    tldr_section = f'''<div class="story-section story-tldr">
        <div class="story-label">TL;DR</div>
        <div class="story-text">{tldr}</div>
        {tldr_i18n}
      </div>''' if tldr else ''

    take_section = f'''<div class="story-section story-take">
        <div class="story-label">Take</div>
        <div class="story-text">{take}</div>
        {take_i18n}
      </div>''' if take else ''

    comments_section = f'''<div class="story-section story-comments">
        <div class="story-label">HN Voices</div>
        {comments_html}
      </div>''' if comments_html else ''

    tags_section = f'<div class="tags">{tags_html}</div>' if tags_html else ''

    id_attr = f'id="{anchor}"' if anchor else ''
    anchor_link = f'<a href="#{anchor}" class="story-anchor">#</a>' if anchor else ''
    hn_label = f'HN#{story_id}' if story_id else 'HN'

    return f'''<article class="story" {id_attr}>
      <h3 class="story-title">
        <a href="{url}" target="_blank">{title}</a>
        {anchor_link}
      </h3>
      {title_i18n}
      <div class="story-meta">
        {points}pts | {comments_count}c | <a href="{hn_url}" target="_blank">{hn_label}</a>
      </div>
      {tldr_section}
      {take_section}
      {comments_section}
      {tags_section}
    </article>'''


def digest_to_html(digest: dict) -> str:
    """Render a digest to HTML."""
    meta = digest.get("meta", {})
    date = meta.get("date", "")
    vibe = escape(digest.get("vibe", ""))
    stories_html = "\n".join(story_to_html(s, date) for s in digest.get("stories", []))

    return f'''<section class="digest">
      <div class="digest-header">
        <div class="digest-date">{date}</div>
        <div class="digest-vibe">{vibe}</div>
      </div>
      {stories_html}
    </section>'''


def generate_sidebar(digests: list) -> str:
    """Generate sidebar with highlights grouped by date."""
    lines = []
    current_date = None

    for digest in digests:
        meta = digest.get("meta", {})
        digest_date = meta.get("date", "")
        date_display = digest_date[:10]
        if date_display != current_date:
            current_date = date_display
            lines.append(f'      <div class="sidebar-date">{date_display}</div>')

        for story in digest.get("stories", []):
            anchor = story_anchor(story.get("id"), digest_date)
            if not anchor:
                continue
            title = escape(story.get("title", ""))[:40]
            if len(story.get("title", "")) > 40:
                title += "..."
            lines.append(f'      <a href="#{anchor}">{title}</a>')

    return "\n".join(lines)


def render_html(digests: list, archive_link: str = None) -> str:
    """Render HTML page from list of digests."""
    template = load_template()
    content = "\n".join(digest_to_html(d) for d in digests)

    if archive_link:
        content += f'''
    <a href="{archive_link}" class="archive-link">
      View older digests →
    </a>'''

    sidebar = generate_sidebar(digests)
    return template.substitute(content=content, sidebar=sidebar)


def story_to_org(story: dict) -> str:
    """Render a story to org-mode format."""
    story_id = story.get("id", "")
    title = story.get("title", "").replace("*", "⁎").replace("[", "［").replace("]", "］")
    url = story.get("url", "")
    hn_url = story.get("hn_url", "")
    points = story.get("points", 0)
    comments_count = story.get("comments_count", 0)
    by = story.get("by", "")
    time = story.get("time", "")
    content = story.get("content", {})
    tags = story.get("tags", [])
    i18n = story.get("i18n", {})

    tag_str = ":" + ":".join(t.lower() for t in tags) + ":" if tags else ""

    org = f"""
** {title} {tag_str}
:PROPERTIES:
:ID:       {story_id}
:URL:      {url}
:HN_URL:   {hn_url}
:POINTS:   {points}
:COMMENTS: {comments_count}
:BY:       {by}
:TIME:     {time}
:END:
"""
    if content.get("tldr"):
        org += f"\n*** TLDR\n{content['tldr']}\n"
    if content.get("take"):
        org += f"\n*** Take\n{content['take']}\n"
    if content.get("comments"):
        org += "\n*** Comments\n"
        for c in content["comments"]:
            org += f"\n**** {c.get('by', 'anon')}\n{c.get('text', '')}\n"

    if i18n:
        org += "\n*** i18n                                                              :i18n:\n"
        for lang, data in i18n.items():
            org += f"\n**** {lang}\n"
            if data.get("tldr"):
                org += f"***** TLDR\n{data['tldr']}\n"
            if data.get("take"):
                org += f"***** Take\n{data['take']}\n"

    return org


def digest_to_org(digest: dict) -> str:
    """Render a digest to org-mode format."""
    meta = digest.get("meta", {})
    date = meta.get("date", "")
    vibe = digest.get("vibe", "").replace("*", "⁎")

    org = f"""#+TITLE: HN Digest {date}
#+DATE: {date}
#+CURATOR: {meta.get('curator', 'claude')}
#+SOURCE: https://hacker-news.firebaseio.com/v0/
#+SCHEMA: v2.0

* Vibe
{vibe}

* Stories
"""
    for story in digest.get("stories", []):
        org += story_to_org(story)

    return org


def digest_to_llms(digest: dict) -> str:
    """Render a digest to llms.txt memory format."""
    meta = digest.get("meta", {})
    date = meta.get("date", "")[:10]
    lines = []

    for story in digest.get("stories", []):
        story_id = story.get("id", "")
        title = story.get("title", "")
        points = story.get("points", 0)
        comments = story.get("comments_count", 0)
        tags = ",".join(story.get("tags", []))
        lines.append(f"{date}|{story_id}|{points}|{comments}|{tags}|{title}")

    return "\n".join(lines)


def load_digests(patterns: list[str]) -> list[dict]:
    """Load all digest JSON files matching patterns."""
    digests = []
    for pattern in patterns:
        for path in sorted(Path(".").glob(pattern)):
            if path.suffix != ".json":
                continue
            try:
                data = json.loads(path.read_text())
                if data.get("meta", {}).get("version") == "2.0":
                    digests.append(data)
                else:
                    print(f"SKIP: {path} (not schema v2.0)", file=sys.stderr)
            except json.JSONDecodeError as e:
                print(f"SKIP: {path} (invalid JSON: {e})", file=sys.stderr)

    # Sort by date descending
    digests.sort(key=lambda d: d.get("meta", {}).get("date", ""), reverse=True)
    return digests


def main():
    p = argparse.ArgumentParser(
        description="Build HTML/org/llms from digest JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("files", nargs="+", help="JSON files or glob patterns")
    p.add_argument("-o", "--output", help="Output file")
    p.add_argument("-f", "--format", choices=["html", "org", "llms"], default="html",
                   help="Output format (default: html)")
    p.add_argument("-d", "--days", type=int, default=0, help="Days to include (0 = all)")
    p.add_argument("-a", "--archive", help="Archive output file (older digests)")
    args = p.parse_args()

    digests = load_digests(args.files)
    if not digests:
        print("No valid v2.0 digests found", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(digests)} digests", file=sys.stderr)

    # Filter by days
    if args.days > 0:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
        recent = [d for d in digests if d.get("meta", {}).get("date", "")[:10] >= cutoff]
        archive = [d for d in digests if d.get("meta", {}).get("date", "")[:10] < cutoff]
    else:
        recent = digests
        archive = []

    # Generate output
    if args.format == "html":
        if args.archive and archive:
            archive_name = Path(args.archive).name
            main_html = render_html(recent, archive_link=archive_name)
            archive_html = render_html(archive, archive_link="index.html")

            if args.output:
                Path(args.output).write_text(main_html)
                print(f"Wrote {args.output} ({len(recent)} digests)", file=sys.stderr)

            Path(args.archive).write_text(archive_html)
            print(f"Wrote {args.archive} ({len(archive)} digests)", file=sys.stderr)
        else:
            html = render_html(recent)
            if args.output:
                Path(args.output).write_text(html)
                print(f"Wrote {args.output} ({len(recent)} digests)", file=sys.stderr)
            else:
                print(html)

    elif args.format == "org":
        # For org, concatenate all digests or output single
        if len(recent) == 1:
            org = digest_to_org(recent[0])
        else:
            org = "\n\n".join(digest_to_org(d) for d in recent)

        if args.output:
            Path(args.output).write_text(org)
            print(f"Wrote {args.output}", file=sys.stderr)
        else:
            print(org)

    elif args.format == "llms":
        lines = []
        for d in digests:  # All digests for memory index
            lines.append(digest_to_llms(d))
        llms = "\n".join(lines)

        if args.output:
            Path(args.output).write_text(llms)
            print(f"Wrote {args.output} ({len(digests)} digests)", file=sys.stderr)
        else:
            print(llms)


if __name__ == "__main__":
    main()
