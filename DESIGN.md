# DESIGN.md -- the material

Read this before touching anything under `assets/` or the HTML the
generator emits (`.claude/skills/hn-digest/scripts/org2html.py`).
`TASTE.md` holds prior rulings; this file holds the material. The one-line
test for any UI change: **a change that makes the surface prettier and
the task harder must fail.** After every edit:

```
~/.claude/skills/design-skill/kit/check.sh --tokens assets/tokens.css assets index.html
```

## Direction

World: **candidate: the sports section** (box score + columnist +
locker-room quotes) on kit **floor**, re-inked. Roll key `20721931`;
pool 9 (my 7 + 2 deck cards by affinity for "AI-written Hacker News
digest archive, 4 editions daily UTC, six languages, story takes and
quoted comments"); assigned candidate #5; chosen 2026-08-26 because the
product is literally a scoreboard (points, comments) with an opinion
column and quoted voices, four editions a day, and every HN reader knows
the sports page by heart.

Hand rejected: teletext-page-grid -- competitive (audience knows Ceefax
302; long prose on a 40x24 grid fails); metro-diagram -- declined (no
network); album-leaf -- declined (needs a void, we need density).
Raises kept: from teletext, *every page has a number* (edition No. in the
dateline and ledger, `editions.json` as the page index); from
metro-diagram, the bilingual name stack (title variants per language,
one shown at a time); from album-leaf, voices accumulate in order of
arrival, each signed (the "From the stands" quotes with their authors).

The five-block promise lives in the first body comment of every page;
this file records the material the promise was kept with.

Scene: 09:00 +8, phone in one hand, coffee in the other; or 23:00 at a
desk. Both themes are real.
Mode: read (front page, edition pages); operate-lite (the archive ledger).
Protected functions: `#s{id}-{MMDDHHMM}` anchors (every Telegram link
ever sent, resolved at the root by `assets/site.js` via `editions.json`);
the six-language switch; light/dark; llms.txt; a 20-minute read.

## Palette: provenance

Day from **specimens/palettes/timetable-paper**: ground = offset stock
(hue 88), ink = carbon black (255), rule = graphite pencil (60), accent =
seal-paste cinnabar (32). Night from **specimens/palettes/split-flap**:
ground = black-painted steel (60), ink = cream silkscreen (85), rule =
the split between flaps (darker than the ground), accent = the amber flap
(80). The irregularity kept: paper and ink are different hues; the rule
is a third material; at night the "line" is darker than the ground, not
lighter. Strategy: restrained -- the accent appears once per page, on the
edition number (the stamp / the amber flap), and on link hover.
`check.sh` palette warnings: none.

## The material

Tokens in `assets/tokens.css` (from `kit/floor/tokens.css`, re-inked as
above). `assets/base.css` is the floor's base, unmodified. `assets/site.css`
uses tokens only.

| Dimension | Value | Law |
|---|---|---|
| Faces | display Barlow Condensed 700 / body Barlow 400-600 / mono JetBrains Mono 400 / CJK Noto Sans SC 400 (all self-hosted as slices under `assets/fonts/`, 2.8 MB on disk, a page loads what it uses) | one family across widths; CJK face first when a CJK language is selected |
| Scale | ratio 1.333, base 1rem, body prose 1.0625rem, leading 1.55 (CJK 1.75) | five levels used: xs sm base 2xl 4xl |
| Measure | 64ch Latin / the floor's 38em CJK | |
| Radius | `--radius: 0` | printed matter has no corners |
| Surfaces | rules only: 3px column rule between stories, 3px double rule under the masthead, 2px under table heads, 1px pencil elsewhere; no cards, no shadows | structure before shadow |
| Density | 0.95 | |
| Motion | still: nothing animates; the floor's reduced-motion block stands | |
| Living element | none | |
| Icons | none; the pilcrow is the permalink | |
| Imagery | none (icon.png is the favicon only) | |
| zh mode | per-element `lang` on translated spans; CJK-Latin spacing written at render time (`pangu()` in the generator); zh/ja/ko leading 1.75 | ja/ko fall to system faces (Hiragino / Apple SD Gothic / Yu / Malgun); Noto JP/KR slices not bundled |

## Signature moves and device ration

Signature: 1. the box score -- five rows, agate, tabular numerals, one
click to each story. 2. the column rule -- stories are cut apart with a
3px ink rule, the way a sports page is pasted up. 3. the edition number
-- every edition has a No., the dateline carries it in the one chroma,
the ledger sorts by it. These and no others.

Per page: one masthead device (the 3px double rule) + one section-label
device (`.kicker`: Barlow Condensed, uppercase, +0.04em, hairline under)
used for "Box score", "The take", "From the stands", and ledger heads.

## Voice

Sports desk, plain: "Box score", "The take", "From the stands", "The
ledger", "Earlier edition / Later edition". No exclamation marks in
chrome. Numbers with thousands separators. The AI's persona lives in the
digests, never in the chrome.

## Check

`check.sh --tokens assets/tokens.css assets index.html` -- 0 FAIL.
WARN with reasons recorded here:

- `zh-voice: exclamation marks in zh copy` -- these are translated HN
  comments quoted verbatim inside `<blockquote>`; the chrome carries
  none. Quoted speech keeps its punctuation.

Not checked by the script, checked by eye on 2026-08-26 at 390 / 768 /
1440 in both themes: no horizontal scroll at 390; the box score keeps
its columns on a phone by dropping the tags column; the margin
scoreboard is hidden under 48rem because the score line under the
headline already carries it.

## Build

`org2html.py digests/*/*/*.org` writes `index.html`, `archive.html`,
`e/YYYY/MM/DD-HHMM.html`, `editions.json`; only files whose content
changed are written. 1,557 editions in ~6 s. The previous build was one
1.4 MB `index.html` plus one 71 MB `archive.html`, rewritten on every
run; the per-edition layout is why the repo history stops growing by
70 MB a day.
