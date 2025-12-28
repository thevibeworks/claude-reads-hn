#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.4.0
"""
Render org-mode HN digests to HTML thread page.

examples:
  %(prog)s digests/*.org -o index.html
  %(prog)s digests/2025/12/15-1100.org  # stdout
"""

import argparse
import sys
from pathlib import Path
from html import escape
from string import Template

sys.path.insert(0, str(Path(__file__).parent))
from org2json import parse_org, digest_to_dict

TEMPLATE_PATH = Path(__file__).parent / "template.html"


def load_template() -> Template:
    """Load HTML template from file."""
    return Template(TEMPLATE_PATH.read_text(encoding="utf-8"))


def story_to_html(story: dict) -> str:
    """Render a story to HTML."""
    story_id = story.get("id", "")
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

    return f'''<article class="story" id="s{story_id}">
      <h3 class="story-title">
        <a href="{url}" target="_blank">{title}</a>
        <a href="#s{story_id}" class="story-anchor">#</a>
      </h3>
      {title_i18n}
      <div class="story-meta">
        {points}pts | {comments_count}c | <a href="{hn_url}" target="_blank">HN#{story_id}</a>
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
            story_id = story.get("id", "")
            title = escape(story.get("title", ""))[:40]
            if len(story.get("title", "")) > 40:
                title += "..."
            lines.append(f'      <a href="#s{story_id}">{title}</a>')

    return "\n".join(lines)


def render_page(digests: list, recent_days: int = 7) -> str:
    """Render full HTML page from list of digests with pagination."""
    from datetime import datetime, timedelta

    template = load_template()

    # Split into recent and archive
    cutoff = (datetime.utcnow() - timedelta(days=recent_days)).strftime("%Y-%m-%d")
    recent = [d for d in digests if d.get("date", "")[:10] >= cutoff]
    archive = [d for d in digests if d.get("date", "")[:10] < cutoff]

    # Render recent content
    content = "\n".join(digest_to_html(d) for d in recent)

    # Render archive as hidden
    if archive:
        archive_content = "\n".join(digest_to_html(d) for d in archive)
        content += f'''
    <div id="archive" class="archive hidden">
      {archive_content}
    </div>
    <button id="load-more" class="load-more" onclick="loadMore()">
      Load {len(archive)} more digests →
    </button>'''

    sidebar = generate_sidebar(recent)  # Only recent in sidebar initially
    return template.substitute(content=content, sidebar=sidebar)


def main():
    parser = argparse.ArgumentParser(description="Render org digests to HTML")
    parser.add_argument("files", nargs="+", help="Org files to render")
    parser.add_argument("-o", "--output", help="Output HTML file")
    parser.add_argument("-d", "--days", type=int, default=7,
                        help="Days to show initially (default: 7)")
    args = parser.parse_args()

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

    html = render_page(digests, recent_days=args.days)

    if args.output:
        Path(args.output).write_text(html)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(html)


if __name__ == "__main__":
    main()
