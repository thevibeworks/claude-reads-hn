#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.5.0
"""
Render org-mode HN digests to HTML.

examples:
  %(prog)s digests/*.org -o index.html                    # all digests
  %(prog)s digests/*.org -o index.html -d 7               # last 7 days in index
  %(prog)s digests/*.org -o index.html -d 7 -a archive.html  # split output
"""

import argparse
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from html import escape
from string import Template

sys.path.insert(0, str(Path(__file__).parent))
from org2json import parse_org, digest_to_dict

TEMPLATE_PATH = Path(__file__).parent / "template.html"

# Canonical anchor format - SINGLE SOURCE OF TRUTH
ANCHOR_PREFIX = "s"  # Story anchors: #s46268854


def story_anchor(story_id) -> str:
    """Generate canonical story anchor ID. Returns empty string if invalid.

    Format: s{numeric_id}
    Examples: s46268854, s12345
    Invalid: s, s0, s-1, sabc
    """
    if story_id is None:
        return ""
    # Convert to int to validate numeric
    try:
        sid = int(story_id)
        if sid <= 0:
            return ""
        return f"{ANCHOR_PREFIX}{sid}"
    except (ValueError, TypeError):
        return ""


def load_template() -> Template:
    """Load HTML template from file."""
    return Template(TEMPLATE_PATH.read_text(encoding="utf-8"))


def story_to_html(story: dict) -> str:
    """Render a story to HTML."""
    raw_id = story.get("id")
    anchor = story_anchor(raw_id)  # Validated anchor or empty
    title = escape(story.get("title", ""))
    url = escape(story.get("url", ""))
    hn_url = escape(story.get("hn_url", ""))
    points = story.get("points", 0)
    comments_count = story.get("comments_count", 0)

    tldr = escape(story.get("tldr", ""))
    take = escape(story.get("take", ""))

    i18n = story.get("i18n", {})

    # Title translations
    title_i18n = "".join(
        f'<div class="i18n-title" data-lang="{lang}">{escape(data["title"])}</div>\n'
        for lang, data in i18n.items() if data.get("title")
    )

    # TLDR translations
    tldr_i18n = "".join(
        f'<span class="i18n-text" data-lang="{lang}">{escape(data["tldr"])}</span>\n'
        for lang, data in i18n.items() if data.get("tldr")
    )

    # Take translations
    take_i18n = "".join(
        f'<span class="i18n-text" data-lang="{lang}">{escape(data["take"])}</span>\n'
        for lang, data in i18n.items() if data.get("take")
    )

    # Tags
    tags_html = "".join(
        f'<span class="tag">#{escape(tag)}</span>'
        for tag in story.get("tags", [])
    )

    # Comments with translations
    comments = story.get("comments", [])
    comments_parts = []
    for idx, c in enumerate(comments):
        comment_text = escape(c.get('text', ''))
        comment_author = escape(c.get('by', ''))

        comment_i18n = "".join(
            f'<div class="comment-i18n" data-lang="{lang}">{escape(data["comments"][idx])}</div>\n'
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

    # Build anchor attributes - only if we have a valid anchor
    id_attr = f'id="{anchor}"' if anchor else ''
    anchor_link = f'<a href="#{anchor}" class="story-anchor">#</a>' if anchor else ''
    hn_label = f'HN#{raw_id}' if raw_id else 'HN'

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
    date = digest.get("date", "")
    vibe = escape(digest.get("vibe", ""))
    stories_html = "\n".join(story_to_html(s) for s in digest.get("stories", []))

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
        date = digest.get("date", "")[:10]
        if date != current_date:
            current_date = date
            lines.append(f'      <div class="sidebar-date">{date}</div>')

        for story in digest.get("stories", []):
            anchor = story_anchor(story.get("id"))
            if not anchor:  # Skip stories without valid anchors
                continue
            title = escape(story.get("title", ""))[:40]
            if len(story.get("title", "")) > 40:
                title += "..."
            lines.append(f'      <a href="#{anchor}">{title}</a>')

    return "\n".join(lines)


def render_page(digests: list, archive_link: str = None) -> str:
    """Render HTML page from list of digests."""
    template = load_template()
    content = "\n".join(digest_to_html(d) for d in digests)

    # Add archive link if provided
    if archive_link:
        content += f'''
    <a href="{archive_link}" class="archive-link">
      View older digests →
    </a>'''

    sidebar = generate_sidebar(digests)
    return template.substitute(content=content, sidebar=sidebar)


def main():
    parser = argparse.ArgumentParser(description="Render org digests to HTML")
    parser.add_argument("files", nargs="+", help="Org files to render")
    parser.add_argument("-o", "--output", help="Output HTML file (index)")
    parser.add_argument("-d", "--days", type=int, default=0,
                        help="Days to include in index (0 = all)")
    parser.add_argument("-a", "--archive", help="Archive output file (older digests)")
    args = parser.parse_args()

    # Parse all digests
    digests = []
    for f in args.files:
        path = Path(f)
        if path.exists():
            content = path.read_text()
            parsed = parse_org(content)
            d = digest_to_dict(parsed)
            if not d.get("stories"):
                print(f"SKIP (no stories): {path}", file=sys.stderr)
                continue
            digests.append(d)

    digests.sort(key=lambda d: d.get("date", ""), reverse=True)

    if args.days > 0 and args.archive:
        # Split mode: recent in index, older in archive
        cutoff = (datetime.now(timezone.utc) - timedelta(days=args.days)).strftime("%Y-%m-%d")
        recent = [d for d in digests if d.get("date", "")[:10] >= cutoff]
        archive = [d for d in digests if d.get("date", "")[:10] < cutoff]

        # Generate index with link to archive
        archive_name = Path(args.archive).name
        index_html = render_page(recent, archive_link=archive_name)

        # Generate archive (no link back, or link to index)
        archive_html = render_page(archive, archive_link="index.html")

        if args.output:
            Path(args.output).write_text(index_html)
            print(f"Wrote {args.output} ({len(recent)} digests)", file=sys.stderr)

        Path(args.archive).write_text(archive_html)
        print(f"Wrote {args.archive} ({len(archive)} digests)", file=sys.stderr)
    else:
        # Single file mode
        html = render_page(digests)
        if args.output:
            Path(args.output).write_text(html)
            print(f"Wrote {args.output} ({len(digests)} digests)", file=sys.stderr)
        else:
            print(html)


if __name__ == "__main__":
    main()
