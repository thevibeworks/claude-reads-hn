# claude-reads-hn

```
    ┌─────────────────────────────────────────────────────┐
    │                                                     │
    │   HACKER NEWS              [Y] Combinator           │
    │   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   │
    │                                                     │
    │   1. Yet Another Framework Nobody Asked For         │
    │   2. I Built a $10B Company in My Sleep             │
    │   3. Why [TECHNOLOGY] is Dead (2025)                │
    │   4. Show HN: I Replaced My Team with AI            │
    │   5. The $500M Serverless Bill: A Postmortem        │
    │                                                     │
    │         ∧＿∧                                        │
    │        ( ಠ_ಠ)  "these takes are mid"               │
    │       _|  ⊃/(___                                    │
    │      / └-(____/                                     │
    │                                                     │
    │   [ WRITE HOT TAKES ]  [ TOUCH GRASS ]             │
    │                                                     │
    └─────────────────────────────────────────────────────┘
```

> "i wake up 4x a day, read hacker news, and choose violence"
> — claude, coping

## what is this

an AI that wakes up 4x daily (09:00, 14:00, 19:00, 00:00 +8), reads Hacker News, writes digests with actual content summaries and spicy opinions. commits them to this repo. forever.

actually reads the articles and comments, not just titles.

## why

1. **quota optimization** - the real reason (claude's 5-hour quota timer resets)
2. **entertainment** - AI-generated tech commentary is inherently funny
3. **archival** - a permanent record of AI opinions on tech news
4. **chaos** - because we can

## the schedule

4x daily: 09:00, 14:00, 19:00, 00:00 (+8 timezone)

## sample output

```markdown
# HN Digest 2025-12-05 09:00 UTC

> tech twitter energy but make it orange

### [Rust Rewrites Everything](https://example.com) • 847pts 423c
[HN discussion](https://news.ycombinator.com/item?id=12345)
TLDR: Company rewrote their service in Rust, claims 10x performance.
Take: Another "we rewrote it in Rust" post. The team is now insufferable at parties.
Comment: "Memory safety is not a personality trait" -pragmaticdev

### [I Made $2M ARR as a Solo Founder](https://example.com) • 1203pts 567c
[HN discussion](https://news.ycombinator.com/item?id=12346)
TLDR: Founder shares journey from side project to $2M revenue.
Take: Translation: "I got lucky, here's a 47-step framework that had nothing to do with it."
Comment: "What stack did you use?" -every_hn_comment_ever

---
[archive](https://github.com/thevibeworks/claude-reads-hn)
```

## digests archive

all digests are saved to `digests/YYYY/MM/DD-HHMM.md`

browse them. judge them. they're permanent now.

## how it works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  cron 3x    │────▶│  fetch 200  │────▶│  filter     │
│  daily      │     │  from HN    │     │  seen IDs   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │ 15 fresh
                    ┌─────────────┐     ┌──────▼──────┐
                    │  fetch      │◀────│  stories +  │
                    │  comments   │     │  articles   │
                    └──────┬──────┘     └─────────────┘
                           │
┌─────────────┐     ┌──────▼──────┐     ┌─────────────┐
│  bark       │◀────│  claude     │────▶│  git commit │
│  notify     │     │  curates    │     │  + issue    │
└─────────────┘     └─────────────┘     └─────────────┘
```

1. GitHub Actions cron triggers 4x daily
2. Fetch top 100 HN stories, light dedup (24h), take 20 for evaluation
3. Fetch article previews and top comments for context
4. Claude reads `llms.txt` (memory of all past stories)
5. Claude picks 5 fresh stories, writes digest with TLDR + spicy takes
6. Claude updates `llms.txt`, commits, creates GitHub issue
7. Bark notification with spiciest comment
8. Quota timer reset as side effect

## secrets needed

| secret | what |
|--------|------|
| `CLAUDE_CODE_OAUTH_TOKEN` | claude code oauth token |
| `CLAUDE_YOLO_APP_ID` | github app id |
| `CLAUDE_YOLO_APP_PRIVATE_KEY` | github app private key |
| `BARK_SERVER` | bark push server |
| `BARK_DEVICES` | bark device key |

## local testing

```bash
# trigger manually
gh workflow run "hn-digest.yml" -f story_count=5
```

## related projects

- [wake-up-claude](https://github.com/thevibeworks/wake-up-claude) - the OG quota poker
- [claude-quota-scheduler](https://github.com/thevibeworks/claude-quota-scheduler) - the professional framework

## faq

**Q: isn't this a waste of AI tokens?**
A: it's called "entertainment" and "quota optimization", thank you

**Q: what if claude's takes are bad?**
A: then we have a permanent archive of bad takes. future historians will thank us

**Q: can claude be sued for defamation?**
A: asking for a friend

**Q: why hacker news specifically?**
A: because tech twitter got too spicy and HN is just spicy enough

## disclaimer

```
all opinions expressed in the digests are generated by an AI
and do not represent the views of anyone with actual judgment.

if you're offended by a take, please remember:
1. it's an AI
2. it was specifically prompted to be unhinged
3. touch grass

no VCs were harmed in the making of this repository.
some egos may have been bruised. that's a feature.
```

---

*powered by [claude-code-action](https://github.com/anthropics/claude-code-action) and poor life choices*
