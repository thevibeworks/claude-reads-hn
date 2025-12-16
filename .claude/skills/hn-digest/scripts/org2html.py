#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 0.2.0
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

sys.path.insert(0, str(Path(__file__).parent))
from org2json import parse_org, digest_to_dict


HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Claude Reads HN</title>
  <meta name="description" content="AI-curated Hacker News digests with spicy takes. 4x daily.">
  <style>
    :root {{
      --bg: #0a0a0a;
      --bg-card: #111111;
      --fg: #e4e4e7;
      --fg-muted: #a1a1aa;
      --fg-dim: #71717a;
      --accent: #f97316;
      --link: #60a5fa;
      --border: #27272a;
      --tldr: #a78bfa;
      --take: #f472b6;
      --comment: #34d399;
    }}
    [data-theme="light"] {{
      --bg: #ffffff;
      --bg-card: #f9fafb;
      --fg: #18181b;
      --fg-muted: #52525b;
      --fg-dim: #a1a1aa;
      --accent: #ea580c;
      --link: #2563eb;
      --border: #e5e7eb;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: Courier, monospace;
      background: var(--bg);
      color: var(--fg);
      line-height: 1.7;
      max-width: 720px;
      margin: 0 auto;
      padding: 2rem 1rem;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid var(--border);
      flex-wrap: wrap;
      gap: 0.5rem;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 1rem;
    }}
    .logo {{ font-weight: bold; font-size: 1.1rem; }}
    .header-links {{ font-size: 0.8rem; }}
    .header-links a {{ color: var(--link); margin-right: 0.75rem; text-decoration: none; }}
    .header-links a:hover {{ text-decoration: underline; }}
    .controls {{ display: flex; align-items: center; gap: 0.5rem; }}
    .controls button {{
      background: none;
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 0.25rem 0.5rem;
      cursor: pointer;
      font-family: inherit;
    }}
    .controls button:hover {{ background: var(--bg-card); }}
    .lang-select {{
      position: relative;
      display: inline-block;
    }}
    .lang-btn {{
      background: none;
      border: 1px solid var(--border);
      color: var(--fg);
      padding: 0.25rem 0.5rem;
      cursor: pointer;
      font-family: inherit;
      font-size: 1rem;
    }}
    .lang-btn:hover {{ background: var(--bg-card); }}
    .lang-menu {{
      display: none;
      position: absolute;
      right: 0;
      top: 100%;
      background: var(--bg-card);
      border: 1px solid var(--border);
      border-radius: 4px;
      min-width: 100px;
      z-index: 100;
    }}
    .lang-select:hover .lang-menu,
    .lang-menu:hover {{ display: block; }}
    .lang-menu button {{
      display: block;
      width: 100%;
      text-align: left;
      background: none;
      border: none;
      color: var(--fg);
      padding: 0.5rem 0.75rem;
      cursor: pointer;
      font-family: inherit;
    }}
    .lang-menu button:hover {{ background: var(--border); }}
    .lang-menu button.active {{ color: var(--accent); }}
    .digest {{ margin-bottom: 3rem; }}
    .digest-header {{ margin-bottom: 1.5rem; }}
    .digest-date {{ font-size: 0.8rem; color: var(--fg-dim); }}
    .digest-vibe {{ font-style: italic; color: var(--fg-muted); margin-top: 0.5rem; }}
    .story {{ margin-bottom: 2rem; padding: 1rem; background: var(--bg-card); border-radius: 6px; }}
    .story-title {{ font-size: 1rem; margin-bottom: 0.5rem; }}
    .story-title a {{ color: var(--fg); text-decoration: none; }}
    .story-title a:hover {{ color: var(--accent); }}
    .story-title-i18n {{ font-size: 0.85rem; color: var(--fg-dim); margin-top: 0.25rem; }}
    .story-meta {{ font-size: 0.75rem; color: var(--fg-dim); margin-bottom: 1rem; }}
    .story-meta a {{ color: var(--link); }}
    .story-section {{ margin-bottom: 1rem; }}
    .story-label {{ font-size: 0.7rem; text-transform: uppercase; margin-bottom: 0.25rem; }}
    .story-tldr .story-label {{ color: var(--tldr); }}
    .story-take .story-label {{ color: var(--take); }}
    .story-comments .story-label {{ color: var(--comment); }}
    .story-text {{ font-size: 0.9rem; color: var(--fg-muted); }}
    .i18n-text {{ margin-top: 0.5rem; padding-top: 0.5rem; border-top: 1px dashed var(--border); color: var(--fg-dim); font-size: 0.85rem; }}
    .i18n-text::before {{ content: "-> "; opacity: 0.5; }}
    .comment {{ padding: 0.75rem 1rem; background: var(--bg); border-radius: 4px; margin-bottom: 0.5rem; border-left: 3px solid var(--comment); }}
    .comment:nth-child(2) {{ border-left-color: var(--take); }}
    .comment:nth-child(3) {{ border-left-color: var(--tldr); }}
    .comment-author {{ font-size: 0.7rem; color: var(--fg-dim); margin-top: 0.5rem; }}
    .comment-i18n {{ font-size: 0.8rem; color: var(--fg-dim); margin-top: 0.25rem; font-style: italic; }}
    .tags {{ margin-top: 1rem; }}
    .tag {{ display: inline-block; background: var(--border); padding: 0.1rem 0.4rem; border-radius: 3px; font-size: 0.75rem; margin-right: 0.25rem; }}
    .hidden {{ display: none; }}
  </style>
</head>
<body>
  <header>
    <div class="header-left">
      <div class="logo">Claude Reads HN</div>
      <div class="header-links">
        <a href="https://github.com/thevibeworks/claude-reads-hn">github</a>
        <a href="https://t.me/claudehn">telegram</a>
      </div>
    </div>
    <div class="controls">
      <button onclick="toggleTheme()" title="Toggle theme">*</button>
      <div class="lang-select">
        <button class="lang-btn" title="Language">A</button>
        <div class="lang-menu">
          <button onclick="setLang('en')" data-lang="en" class="active">English</button>
          <button onclick="setLang('zh')" data-lang="zh">中文</button>
          <button onclick="setLang('ja')" data-lang="ja">日本語</button>
          <button onclick="setLang('ko')" data-lang="ko">한국어</button>
          <button onclick="setLang('es')" data-lang="es">Español</button>
          <button onclick="setLang('de')" data-lang="de">Deutsch</button>
        </div>
      </div>
    </div>
  </header>
  <main id="feed">
{content}
  </main>
  <script>
    let currentLang = 'en';
    function safeStorage(key, value) {{
      try {{
        if (value === undefined) return localStorage.getItem(key);
        localStorage.setItem(key, value);
        return value;
      }} catch (e) {{ return null; }}
    }}
    function toggleTheme() {{
      const html = document.documentElement;
      const isDark = html.getAttribute('data-theme') === 'dark';
      const newTheme = isDark ? 'light' : 'dark';
      html.setAttribute('data-theme', newTheme);
      safeStorage('hn-theme', newTheme);
    }}
    function setLang(lang) {{
      currentLang = lang;
      document.querySelectorAll('.lang-menu button[data-lang]').forEach(b => {{
        b.classList.toggle('active', b.dataset.lang === lang);
      }});
      document.querySelectorAll('.i18n-text').forEach(el => {{
        el.classList.toggle('hidden', el.dataset.lang !== lang);
      }});
      document.querySelectorAll('.i18n-text[data-lang="en"]').forEach(el => {{
        el.classList.add('hidden');
      }});
      safeStorage('hn-lang', lang);
    }}
    (function init() {{
      const savedTheme = safeStorage('hn-theme');
      if (savedTheme) document.documentElement.setAttribute('data-theme', savedTheme);
      const savedLang = safeStorage('hn-lang');
      if (savedLang && savedLang !== 'en') setLang(savedLang);
    }})();
  </script>
</body>
</html>'''


def story_to_html(story: dict, lang: str = "en") -> str:
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
    title_i18n = ""
    for ilang, data in i18n.items():
        if data.get("title"):
            title_i18n += f'<div class="story-title-i18n i18n-text" data-lang="{ilang}">{escape(data["title"])}</div>\n'

    # TLDR translations
    tldr_i18n = ""
    for ilang, data in i18n.items():
        if data.get("tldr"):
            tldr_i18n += f'<div class="i18n-text" data-lang="{ilang}">{escape(data["tldr"])}</div>\n'

    # Take translations
    take_i18n = ""
    for ilang, data in i18n.items():
        if data.get("take"):
            take_i18n += f'<div class="i18n-text" data-lang="{ilang}">{escape(data["take"])}</div>\n'

    tags_html = ""
    for tag in story.get("tags", []):
        tags_html += f'<span class="tag">#{escape(tag)}</span>'

    # Comments with translations
    comments_html = ""
    comments = story.get("comments", [])
    for idx, c in enumerate(comments):
        comment_text = escape(c.get('text', ''))
        comment_author = escape(c.get('by', ''))

        # Check for comment translations in i18n
        comment_i18n = ""
        for ilang, data in i18n.items():
            comment_translations = data.get("comments", [])
            if idx < len(comment_translations) and comment_translations[idx]:
                comment_i18n += f'<div class="comment-i18n i18n-text" data-lang="{ilang}">{escape(comment_translations[idx])}</div>\n'

        comments_html += f'''<div class="comment">
          "{comment_text}"
          <div class="comment-author">-- {comment_author}</div>
          {comment_i18n}
        </div>'''

    return f'''<article class="story" id="{story_id}">
      <h3 class="story-title"><a href="{url}" target="_blank">{title}</a></h3>
      {title_i18n}
      <div class="story-meta">
        {points}pts | {comments_count}c | <a href="{hn_url}" target="_blank">HN#{story_id}</a>
      </div>
      {f'''<div class="story-section story-tldr">
        <div class="story-label">TL;DR</div>
        <div class="story-text">{tldr}</div>
        {tldr_i18n}
      </div>''' if tldr else ''}
      {f'''<div class="story-section story-take">
        <div class="story-label">Take</div>
        <div class="story-text">{take}</div>
        {take_i18n}
      </div>''' if take else ''}
      {f'''<div class="story-section story-comments">
        <div class="story-label">HN Voices</div>
        {comments_html}
      </div>''' if comments_html else ''}
      {f'<div class="tags">{tags_html}</div>' if tags_html else ''}
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


def render_page(digests: list) -> str:
    """Render full HTML page from list of digests."""
    content = "\n".join(digest_to_html(d) for d in digests)
    return HTML_TEMPLATE.format(content=content)


def main():
    parser = argparse.ArgumentParser(description="Render org digests to HTML")
    parser.add_argument("files", nargs="+", help="Org files to render")
    parser.add_argument("-o", "--output", help="Output HTML file")
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

    html = render_page(digests)

    if args.output:
        Path(args.output).write_text(html)
        print(f"Wrote {args.output}", file=sys.stderr)
    else:
        print(html)


if __name__ == "__main__":
    main()
