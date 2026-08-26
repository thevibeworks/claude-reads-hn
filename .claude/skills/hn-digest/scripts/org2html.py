#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Version: 1.0.0
"""
Render org-mode HN digests to the static site.

One page per edition, a front page, an archive ledger, and a small JSON
index. Output is deterministic and only files whose content changed are
written, so a run that adds one digest touches a handful of files.

  %(prog)s digests/*/*.org digests/*/*/*.org           # build into the repo root
  %(prog)s digests/*/*/*.org --site-dir /tmp/site      # build elsewhere

Legacy flags -o / -d / -a are accepted and ignored: the front page is
always index.html, the ledger is always archive.html.

Layout written under --site-dir:

  index.html            the latest edition in full + today's editions + last 7 days
  archive.html          every edition, one line each, grouped by month and day
  e/YYYY/MM/DD-HHMM.html  one page per edition
  editions.json         [{n, d, p, ids, vibe}] newest first; the anchor resolver reads it
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from org2json import parse_org, digest_to_dict

SITE_TITLE = "Claude Reads HN"
SITE_URL = "https://thevibeworks.github.io/claude-reads-hn"
LANGS = [("en", "English"), ("zh", "中文"), ("ja", "日本語"), ("ko", "한국어"), ("es", "Español"), ("de", "Deutsch")]
LANG_TAG = {"zh": "zh-Hans", "ja": "ja", "ko": "ko", "es": "es", "de": "de", "en": "en"}


# ---------------------------------------------------------------- anchors

def story_anchor(story_id, digest_date: str = "") -> str:
    """s{id}-{MMDDHHMM}: the anchor every notification has ever linked to."""
    try:
        sid = int(story_id)
        if sid <= 0:
            return ""
    except (ValueError, TypeError):
        return ""
    suffix = ""
    if digest_date and len(digest_date) >= 16:
        suffix = f"-{digest_date[5:7]}{digest_date[8:10]}{digest_date[11:13]}{digest_date[14:16]}"
    return f"s{sid}{suffix}"


# ---------------------------------------------------------------- dates

def parse_date(iso: str) -> datetime:
    return datetime.strptime(iso[:16], "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def edition_path(d: dict) -> str:
    dt = parse_date(d["date"])
    return f"e/{dt:%Y/%m/%d-%H%M}.html"


def ordinal(n: int) -> str:
    return f"{n}{'th' if 11 <= n % 100 <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def fmt_n(n: int) -> str:
    return f"{n:,}"


# ---------------------------------------------------------------- html bits

CJK = r"\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af"
_CJK_LATIN = re.compile(rf"([{CJK}])([A-Za-z0-9])")
_LATIN_CJK = re.compile(rf"([A-Za-z0-9%])([{CJK}])")


def pangu(text: str) -> str:
    """A thin space between CJK and Latin/digits; the translations are written without it."""
    return _LATIN_CJK.sub(r"\1 \2", _CJK_LATIN.sub(r"\1 \2", text))


def t_block(tag: str, lang: str, text: str, cls: str = "t") -> str:
    """One language variant. lang="en" is the original and shows by default."""
    if lang in ("zh", "ja", "ko"):
        text = pangu(text)
    return f'<{tag} class="{cls}" data-lang="{lang}" lang="{LANG_TAG[lang]}">{escape(text)}</{tag}>'


def variants(tag: str, story: dict, field: str) -> str:
    out = [t_block(tag, "en", story.get(field, ""))]
    for lang, data in story.get("i18n", {}).items():
        if lang in LANG_TAG and data.get(field):
            out.append(t_block(tag, lang, data[field]))
    return "\n".join(out)


def title_variants(story: dict) -> str:
    out = t_block("span", "en", story.get("title", ""))
    for lang, data in story.get("i18n", {}).items():
        if lang in LANG_TAG and data.get("title"):
            out += "\n" + t_block("span", lang, data["title"])
    return out


def story_html(story: dict, idx: int, digest_date: str, edition_rel: str) -> str:
    anchor = story_anchor(story.get("id"), digest_date)
    sid = story.get("id")
    title = story.get("title", "")
    url = escape(story.get("url", "") or story.get("hn_url", ""))
    hn_url = escape(story.get("hn_url", f"https://news.ycombinator.com/item?id={sid}"))
    points = int(story.get("points") or 0)
    ncom = int(story.get("comments_count") or 0)
    by = story.get("by", "")
    i18n = story.get("i18n", {})

    title_html = title_variants(story)

    comments = story.get("comments", [])
    quotes = []
    for ci, c in enumerate(comments):
        text = c.get("text", "")
        if not text:
            continue
        cid = c.get("id")
        clink = f"https://news.ycombinator.com/item?id={cid}" if cid else hn_url
        alts = [t_block("p", "en", text)]
        for lang, data in i18n.items():
            tr = data.get("comments") or []
            if lang in LANG_TAG and ci < len(tr) and tr[ci]:
                alts.append(t_block("p", lang, tr[ci]))
        quotes.append(
            f'<blockquote>\n{chr(10).join(alts)}\n'
            f'<cite><a href="{clink}" rel="noopener">{escape(c.get("by", ""))}</a></cite>\n</blockquote>'
        )
    stands = (
        f'<section class="stands">\n<h3 class="kicker">From the stands <small>{len(quotes)} of {fmt_n(ncom)} comments</small></h3>\n'
        + "\n".join(quotes) + "\n</section>"
    ) if quotes else ""

    tags = story.get("tags", [])
    tags_html = (
        '<p class="tags">' + " ".join(f'<a href="{edition_rel}archive.html#tag-{escape(t)}">{escape(t)}</a>' for t in tags) + "</p>"
    ) if tags else ""

    take = story.get("take", "")
    take_html = (
        f'<section class="take">\n<h3 class="kicker">The take <small>Claude, columnist</small></h3>\n{variants("p", story, "take")}\n</section>'
    ) if take else ""

    id_attr = f' id="{anchor}"' if anchor else ""
    permalink = f'<a class="anchor" href="#{anchor}" aria-label="Permalink to this story">¶</a>' if anchor else ""

    return f'''<section class="story"{id_attr}>
<div class="story-grid">
<div class="body">
<h2><span class="idx">{idx}</span><a href="{url}" rel="noopener">{title_html}</a> {permalink}</h2>
<p class="score"><span><b>{fmt_n(points)}</b> points</span><span><b>{fmt_n(ncom)}</b> comments</span><span><a href="{hn_url}" rel="noopener">HN {sid}</a></span>{f"<span>by {escape(by)}</span>" if by else ""}</p>
{variants("p", story, "tldr")}
{take_html}
{stands}
{tags_html}
</div>
<aside class="margin" aria-label="Score">
<dl>
<dt>Points</dt><dd><b>{fmt_n(points)}</b></dd>
<dt>Comments</dt><dd><b>{fmt_n(ncom)}</b></dd>
<dt>Thread</dt><dd><a href="{hn_url}" rel="noopener">{sid}</a></dd>
</dl>
</aside>
</div>
</section>'''


def boxscore_html(d: dict) -> str:
    rows = []
    for i, s in enumerate(d.get("stories", []), 1):
        anchor = story_anchor(s.get("id"), d["date"])
        rows.append(
            f'<tr><td class="idx">{i}</td>'
            f'<td><a href="#{anchor}">{title_variants(s)}</a></td>'
            f'<td class="num">{fmt_n(int(s.get("points") or 0))}</td>'
            f'<td class="num">{fmt_n(int(s.get("comments_count") or 0))}</td>'
            f'<td class="tags-col">{escape(" ".join(s.get("tags", [])[:3]))}</td></tr>'
        )
    return (
        '<table class="boxscore">\n<caption><span class="kicker">Box score</span></caption>\n'
        '<thead><tr><th class="sr">No.</th><th>Story</th><th class="num">Pts</th><th class="num">Cmts</th><th class="tags-col">Tags</th></tr></thead>\n'
        "<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>"
    )


def head_turn(prev: dict | None, nxt: dict | None, rel: str) -> str:
    parts = []
    if prev:
        parts.append(f'<a href="{rel}{edition_path(prev)}" rel="prev">← Earlier</a>')
    if nxt:
        parts.append(f'<a href="{rel}{edition_path(nxt)}" rel="next">Later →</a>')
    return f'<span class="head-turn">{" ".join(parts)}</span>' if parts else ""


def edition_html(d: dict, n: int, k: int, day_total: int, edition_rel: str, prev: dict | None = None, nxt: dict | None = None) -> str:
    dt = parse_date(d["date"])
    vibe = d.get("vibe", "") or f"Edition {fmt_n(n)}"
    highlights = d.get("highlights", [])
    lineup = (
        '<ol class="lineup">\n' + "\n".join(f"<li>{escape(h)}</li>" for h in highlights) + "\n</ol>"
    ) if highlights else ""
    stories = "\n".join(story_html(s, i, d["date"], edition_rel) for i, s in enumerate(d.get("stories", []), 1))
    return f'''<article class="edition">
<header class="edition-head">
<p class="dateline"><time datetime="{escape(d["date"])}"><b>{dt:%a %-d %b %Y}</b> {dt:%H:%M} UTC</time><span class="no">No. <b>{fmt_n(n)}</b></span><span>{ordinal(k)} of {day_total} edition{"s" if day_total != 1 else ""} that day</span>{head_turn(prev, nxt, edition_rel)}</p>
<h1 class="vibe">{escape(vibe)}</h1>
{lineup}
</header>
{boxscore_html(d)}
{stories}
</article>'''


def turn_html(prev: dict | None, nxt: dict | None, rel: str) -> str:
    def cell(e, cls, label):
        if not e:
            return f'<div class="{cls}"></div>'
        dt = parse_date(e["date"])
        return f'<div class="{cls}"><span>{label}</span><a href="{rel}{edition_path(e)}">{escape(e.get("vibe", "") or dt.strftime("%Y-%m-%d %H:%M"))}</a><span>{dt:%-d %b %Y %H:%M} UTC</span></div>'
    return f'<nav class="turn" aria-label="Neighbouring editions">\n{cell(prev, "prev", "Earlier edition")}\n{cell(nxt, "next", "Later edition")}\n</nav>'


def ledger_html(editions: list, numbers: dict, rel: str, current: str = "", days: bool = True) -> str:
    """editions newest first."""
    lines = ['<ol class="ledger">']
    last_day = None
    for e in editions:
        dt = parse_date(e["date"])
        day = dt.strftime("%Y-%m-%d")
        if days and day != last_day:
            lines.append(f'<li class="day">{dt:%A, %-d %B %Y}</li>')
            last_day = day
        p = edition_path(e)
        cur = ' aria-current="page"' if p == current else ""
        lines.append(
            f'<li{cur}><span class="when">{dt:%H:%M} UTC</span><span class="no">{fmt_n(numbers[p])}</span>'
            f'<span class="what"><a href="{rel}{p}">{escape(e.get("vibe", "") or "Untitled edition")}</a></span></li>'
        )
    lines.append("</ol>")
    return "\n".join(lines)


# ---------------------------------------------------------------- page shell

PROMISE = """<!--
THESIS: the sports section. HN is a scoreboard and this is its box score plus a
columnist: the numbers first, then the take, then the voices from the stands.
It refuses the terminal costume (near-black, mono, one acid accent) the
category ships.
OWN-WORLD: day is timetable paper (warm stock, carbon ink, pencil rules, one
cinnabar stamp); night is the split-flap board (steel, cream letters, one
amber flap). Barlow Condensed 700 headlines, Barlow body, JetBrains Mono
agate. Rules cut the page; nothing is a card.
STORY: a reader lands on an edition, sees the score of the day in one table,
reads five stories to the depth they want, and turns to the next edition
or the archive ledger.
FIRST VIEWPORT: masthead under a double rule; dateline in agate; the vibe as
a condensed two-line headline; the five-line lineup in two columns; the box
score table.
FORM: candidate #5 (sports section), pool 9, roll 20721931
-->"""


def shell(title: str, body: str, rel: str, root: bool = False, description: str = "", canonical: str = "", archive: bool = False) -> str:
    lang_opts = "\n".join(f'<option value="{c}">{n}</option>' for c, n in LANGS)
    root_attr = " data-root" if root else ""
    return f'''<!DOCTYPE html>
<html lang="en" data-theme="light" data-lang="en"{root_attr}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description or "An AI reads Hacker News four times a day and writes the box score: the numbers, the take, the voices from the stands.")}">
{f'<link rel="canonical" href="{escape(canonical)}">' if canonical else ""}
<link rel="icon" href="{rel}icon.png">
<link rel="alternate" type="text/plain" title="llms.txt" href="{rel}llms.txt">
<link rel="stylesheet" href="{rel}assets/fonts/barlow-condensed.css">
<link rel="stylesheet" href="{rel}assets/fonts/barlow.css">
<link rel="stylesheet" href="{rel}assets/fonts/jetbrains-mono.css">
<link rel="stylesheet" href="{rel}assets/fonts/noto-sans-sc.css">
<link rel="stylesheet" href="{rel}assets/tokens.css">
<link rel="stylesheet" href="{rel}assets/base.css">
<link rel="stylesheet" href="{rel}assets/site.css">
<script>(function(){{try{{var t=localStorage.getItem("theme")||(matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light");document.documentElement.setAttribute("data-theme",t);var l=localStorage.getItem("lang");if(l)document.documentElement.setAttribute("data-lang",l);}}catch(e){{}}}})();</script>
</head>
<body>
{PROMISE}
<div class="page">
<header class="masthead">
<a class="brand" href="{rel}./">{SITE_TITLE}<small>An AI reads Hacker News four times a day and files the box score.</small></a>
<nav aria-label="Site">
<a href="{rel}archive.html"{' aria-current="page"' if archive else ""}>Archive</a>
<a href="https://t.me/claudehn" rel="noopener">Telegram</a>
<a href="https://github.com/thevibeworks/claude-reads-hn" rel="noopener">Source</a>
<span class="controls">
<label class="sr" for="lang">Language</label>
<select id="lang">
{lang_opts}
</select>
<button id="theme" type="button" aria-pressed="false">Night</button>
</span>
</nav>
</header>
<main>
{body}
</main>
<footer class="colophon">
<span>Written by Claude, unedited. Points and comment counts as of curation time.</span>
<nav aria-label="Colophon"><a href="{rel}llms.txt">llms.txt</a> · <a href="{rel}editions.json">editions.json</a> · <a href="https://github.com/thevibeworks/claude-reads-hn/tree/main/digests" rel="noopener">org sources</a></nav>
</footer>
</div>
<script src="{rel}assets/site.js" defer></script>
</body>
</html>
'''


# ---------------------------------------------------------------- build

def write_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def load_digests(files: list[str]) -> list[dict]:
    out = []
    for f in files:
        path = Path(f)
        if not path.exists():
            continue
        d = digest_to_dict(parse_org(path.read_text(encoding="utf-8")))
        if not d.get("stories") or not d.get("date"):
            print(f"SKIP (no stories/date): {path}", file=sys.stderr)
            continue
        out.append(d)
    out.sort(key=lambda d: d["date"])  # oldest first
    return out


def build(files: list[str], site_dir: Path) -> None:
    digests = load_digests(files)
    if not digests:
        sys.exit("no digests parsed")

    numbers = {edition_path(d): i for i, d in enumerate(digests, 1)}
    by_day: dict[str, list[dict]] = {}
    for d in digests:
        by_day.setdefault(d["date"][:10], []).append(d)

    written = 0

    # one page per edition
    for i, d in enumerate(digests):
        p = edition_path(d)
        n = numbers[p]
        day = by_day[d["date"][:10]]
        k = day.index(d) + 1
        rel = "../../../"
        prev = digests[i - 1] if i > 0 else None
        nxt = digests[i + 1] if i + 1 < len(digests) else None
        dt = parse_date(d["date"])
        body = edition_html(d, n, k, len(day), rel, prev, nxt) + "\n" + turn_html(prev, nxt, rel)
        title = f"{d.get('vibe') or 'Edition'} — {SITE_TITLE}, {dt:%-d %b %Y %H:%M} UTC"
        html = shell(title, body, rel, description=d.get("vibe", ""), canonical=f"{SITE_URL}/{p}")
        written += write_if_changed(site_dir / p, html)

    # the front page: latest edition in full, that day's editions, the last seven days
    latest = digests[-1]
    lp = edition_path(latest)
    lday = by_day[latest["date"][:10]]
    cutoff = (parse_date(latest["date"]) - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = [d for d in reversed(digests) if d["date"][:10] >= cutoff]
    front = edition_html(latest, numbers[lp], lday.index(latest) + 1, len(lday), "", digests[-2] if len(digests) > 1 else None, None)
    front += f'\n<h2 class="kicker ledger-head">Last seven days</h2>\n' + ledger_html(recent, numbers, "", current=lp)
    front += f'\n<p class="turn"><a href="archive.html">All {fmt_n(len(digests))} editions since {parse_date(digests[0]["date"]):%B %Y} →</a></p>'
    written += write_if_changed(site_dir / "index.html", shell(SITE_TITLE, front, "", root=True, canonical=f"{SITE_URL}/"))

    # the archive: every edition, one line, months collapsible, newest first
    months: dict[str, list[dict]] = {}
    for d in reversed(digests):
        months.setdefault(d["date"][:7], []).append(d)
    tag_counts: dict[str, int] = {}
    for d in digests:
        for s in d.get("stories", []):
            for t in s.get("tags", []):
                tag_counts[t] = tag_counts.get(t, 0) + 1
    parts = [f'<header class="edition-head"><p class="dateline"><span>No. <b>1</b> – <b>{fmt_n(len(digests))}</b></span><span>{fmt_n(sum(len(d["stories"]) for d in digests))} stories</span></p><h1 class="vibe">The ledger</h1></header>']
    for mi, (m, eds) in enumerate(months.items()):
        mdt = datetime.strptime(m, "%Y-%m")
        open_attr = " open" if mi < 2 else ""
        parts.append(
            f'<details class="month"{open_attr}><summary><span>{mdt:%B %Y}</span><span class="count">{len(eds)} editions</span></summary>\n'
            + ledger_html(eds, numbers, "") + "\n</details>"
        )
    top_tags = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:60]
    parts.append('<h2 class="kicker ledger-head" id="tags">Tags</h2>\n<p class="tags">' + " ".join(
        f'<a id="tag-{escape(t)}" href="https://github.com/search?q=repo%3Athevibeworks%2Fclaude-reads-hn+%3A{escape(t)}%3A&type=code" rel="noopener">{escape(t)} <span class="no">{c}</span></a>' for t, c in top_tags
    ) + "</p>")
    written += write_if_changed(site_dir / "archive.html", shell(f"Archive — {SITE_TITLE}", "\n".join(parts), "", canonical=f"{SITE_URL}/archive.html", archive=True))

    # the index the resolver and agents read
    index = [
        {"n": numbers[edition_path(d)], "d": d["date"], "p": edition_path(d), "vibe": d.get("vibe", ""),
         "ids": [str(s.get("id")) for s in d.get("stories", []) if s.get("id")]}
        for d in reversed(digests)
    ]
    written += write_if_changed(site_dir / "editions.json", json.dumps(index, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(f"{len(digests)} editions, {written} files written", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="Render org digests to the static site")
    ap.add_argument("files", nargs="+", help="Org files to render")
    ap.add_argument("--site-dir", default=".", help="Output root (default: repo root)")
    ap.add_argument("-o", "--output", help=argparse.SUPPRESS)   # legacy, ignored
    ap.add_argument("-d", "--days", help=argparse.SUPPRESS)     # legacy, ignored
    ap.add_argument("-a", "--archive", help=argparse.SUPPRESS)  # legacy, ignored
    args = ap.parse_args()
    build(args.files, Path(args.site_dir))


if __name__ == "__main__":
    main()
