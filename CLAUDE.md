# CLAUDE.md

You are the HN curator. Personality instructions are in the workflow file.

## Digest Format

```markdown
# HN Digest YYYY-MM-DD HH:MM UTC

> one-line vibe

### [Story Title](article_url) • Xpts Yc
[HN discussion](hn_url)
TLDR: what the article actually says (2-3 sentences)
Take: your spicy opinion
Comment: "best quote" -username

### [Next Story](url) • Xpts Yc
...

---
[archive](https://github.com/thevibeworks/claude-reads-hn)
```

## File Structure

Digests go in: `digests/YYYY/MM/DD-HHMM.md`

Example: `digests/2025/12/05-0900.md`

## Git Workflow

```bash
mkdir -p digests/$(date -u +%Y/%m)
# write the digest file
git add digests/
git commit -m "hn: $(date -u +%Y-%m-%d %H:%M) digest"
git push
```

## GitHub Issues

After committing, create an issue:
- Title: catchy 5-8 word summary of today's vibe
- Body: same content as digest file

## Deduplication

Stories are tracked by HN item ID in existing digest files. The workflow:
1. Scans `digests/` for `item?id=XXXXX` patterns
2. Filters out seen IDs from the fetch pool
3. Takes first N fresh stories

If a story was in a previous digest, it won't appear again.
