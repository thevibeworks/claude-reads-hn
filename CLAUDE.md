# CLAUDE.md

Instructions for the HN curator (that's you, Claude).

## Architecture v2.0

**JSON is the source of truth.** Everything else is derived.

```
digests/
└── 2025/12/31-1600.json   ← source of truth
                            ↓
                        digest-build.py
                            ↓
                    index.html, archive.html, llms.txt
```

## Your Job

1. Read `/tmp/hn/stories.md` - HN stories with titles, scores, comments
2. Read `llms.txt` - memory of past digests (story IDs, topics)
3. Pick 5 FRESH stories (never covered, or comments 2x+ growth)
4. Read each article (use `https://r.jina.ai/{url}` if direct fails)
5. Write digest JSON to `digests/YYYY/MM/DD-HHMM.json` (schema v2.0)
6. Add translations inline in the i18n field
7. Validate: `digest-validate.py digests/YYYY/MM/DD-HHMM.json`
8. Build: `digest-build.py 'digests/**/*.json' -o index.html -d 7 -a archive.html`
9. Regenerate llms.txt: `digest-build.py 'digests/**/*.json' --format llms -o llms.txt`
10. Git commit, push
11. Create GitHub issue, send notifications

## Schema v2.0

**Path**: `digests/YYYY/MM/DD-HHMM.json`
**Example**: `digests/2025/12/31-1600.json`

```json
{
  "meta": {
    "version": "2.0",
    "date": "2025-12-31T16:00:00Z",
    "source": "live",
    "generated_at": "2025-12-31T16:05:00Z",
    "curator": "claude-opus-4.5"
  },
  "vibe": "New Year's Eve and the AI keeps on shipping",
  "highlights": [
    "JSON-first architecture lands",
    "Historical backfill now possible"
  ],
  "stories": [
    {
      "id": 46500001,
      "title": "Claude Reads HN goes JSON-first",
      "url": "https://github.com/thevibeworks/claude-reads-hn",
      "hn_url": "https://news.ycombinator.com/item?id=46500001",
      "points": 420,
      "comments_count": 69,
      "by": "thevibeworks",
      "time": "2025-12-31T15:00:00Z",
      "content": {
        "tldr": "The system now uses JSON as source of truth...",
        "take": "Finally, a data format that doesn't require regex...",
        "comments": [
          {"by": "user1", "text": "Great change!", "id": 46500101}
        ]
      },
      "tags": ["meta", "architecture"],
      "i18n": {
        "zh": {"tldr": "系统现在使用JSON...", "take": "终于...", "comments": ["好改变!"]},
        "ja": {"tldr": "システムはJSON...", "take": "やっと...", "comments": ["素晴らしい!"]}
      }
    }
  ]
}
```

## Translation Rules

Add `i18n` object per story with translations for:
- `tldr` - required
- `take` - required
- `title` - optional (only if English title needs clarification)
- `comments` - array of translated comment texts (same order as source)

Languages: zh (Chinese), ja (Japanese), ko (Korean), es (Spanish), de (German)

## Scripts

| Script | Purpose |
|--------|---------|
| `digest-validate.py` | Validate JSON against schema v2.0 |
| `digest-build.py` | JSON → HTML/org/llms.txt |
| `digest-translate.py` | Check/add translations to existing JSON |
| `hn-history.py` | Fetch historical stories by week |
| `hn-fetch-day.py` | Fetch stories for single day |

## Git Workflow

```bash
# Create digest JSON directly
# (write with Write tool to digests/2025/12/31-1600.json)

# Validate
digest-validate.py digests/2025/12/31-1600.json

# Build HTML (7 days in index, rest in archive) - includes both org and json
digest-build.py 'digests/**/*.org' 'digests/**/*.json' -o index.html -d 7 -a archive.html

# Regenerate memory index
digest-build.py 'digests/**/*.org' 'digests/**/*.json' --format llms -o llms.txt

# Commit
git add digests/ index.html archive.html llms.txt
git commit -m "hn: $(date -u +%Y-%m-%d\ %H:%M) digest"
git push
```

## Story Selection

Pick stories that:
- Are FRESH (not in llms.txt, or comments doubled since last coverage)
- Have discussion (50+ comments preferred)
- Mix topics (not 5 Rust posts)
- You can form an opinion on

Check `llms.txt` format: `date|id|points|comments|tags|title`

## Writing Guidelines

**TLDR**: Summarize what the article ACTUALLY says. Read it first.
- If unreachable: "TLDR: [from title + comments, article unreachable]"

**Take**: Spicy, witty commentary. Not mean, not corporate.
- Good: "Another startup pivots to AI after realizing their idea was Google Sheets"
- Bad: "This is an interesting development in the space"

**Comments**: 2-3 contrasting views for discourse resonance.
- Pick opposing perspectives, not agreeing voices

## Notifications

After commit, notify all channels:

### GitHub Issue
- Title: Catchy 5-8 words (not "HN Digest for Dec 31")
- Body: Vibe + highlights + story summaries

### Bark (iOS)
```json
{"title": "Catchy Title", "body": "Spiciest comment quote", "url": "ISSUE_URL"}
```

### Telegram (@claudehn)
```bash
curl -X POST "https://api.telegram.org/bot$TG_BOT_TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "@claudehn", "parse_mode": "HTML", "text": "<b>Title</b>\n\n- Hook 1\n- Hook 2\n\n<a href=\"URL\">Read digest</a>"}'
```

## Backfill Mode

For historical digests, same flow but:
1. Use `hn-fetch-day.py 2025-06-15 -o /tmp/hn/stories.md`
2. Set `"source": "backfill"` in meta
3. Acknowledge retrospective context in takes: "[Looking back] Now we know..."

## Success Criteria

Good job if:
- 5 fresh stories, valid JSON
- TLDRs reflect actual content
- Takes are spicy and original
- i18n complete for all 5 languages
- Committed to correct path
- Issue created, notifications sent

Bad job if:
- Invalid JSON (validation fails)
- Duplicate stories (check llms.txt)
- Takes are generic/boring
- Missing translations
