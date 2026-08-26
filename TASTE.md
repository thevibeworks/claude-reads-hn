# TASTE.md -- prior rulings

Scars from real rejections. Each carries its why; a scar without a why
is a ban, and bans fossilize. Read this before any design verdict;
delete a scar the moment its expiry condition arrives. Material lives
in DESIGN.md.

## 2026-08-26 rejected: the terminal costume

Why: the 2025 site was near-black, Courier, one orange accent, a sticky
sidebar of truncated titles -- the exact page the "AI reads HN" category
ships, so it told a visitor nothing about *this* product. Also 71 MB of
archive in one file.
Reuse: if the category could guess the look, it is not designed. The
standing exit (dark + mono + acid accent) stays off the table unless a
brief names a factual reason.
Expires: never (structural).

## 2026-08-26 rejected: one page for everything

Why: `index.html` (7 days) + `archive.html` (everything else) meant the
archive was a 71 MB download that phones could not open, and every
5-hour run rewrote both, so git history grew by ~70 MB a day.
Reuse: one page per edition; ledgers list, they do not embed; a build
writes only what changed.
Expires: never (structural).

## 2026-08-26 rejected: showing the translation under the original

Why: six languages stacked under every paragraph made each story six
times as tall and the page unreadable in any of them.
Reuse: one language at a time, chosen once, remembered; the original is
one of the six.
Expires: if a reader asks for side-by-side (then a two-column mode, not
a stack).

## 2026-08-26 rejected: `#tag` glyphs on tags

Why: `#fda` is a valid hex color and tripped the raw-color check; more
to the point, the octothorpe was decoration -- the tag is the word.
Reuse: tags are words in the mono, ruled apart by space.
Expires: never.

## 2026-08-26 rejected: the scoreboard margin on phones

Why: the sticky Points / Comments / Thread aside, fine at 1440, dropped
below the story on a phone and repeated the score line already under
the headline.
Reuse: a margin element must earn a second placement on the phone or be
hidden there.
Expires: never (structural).
