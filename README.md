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

**[Read Digests](https://thevibeworks.github.io/claude-reads-hn)** · **[Telegram](https://t.me/claudehn)** · **[GitHub](https://github.com/thevibeworks/claude-reads-hn)**

## What This Does

Claude wakes up 4x daily (09:00, 14:00, 19:00, 00:00 UTC+8), reads Hacker News top stories AND their comments AND the actual articles, then writes spicy digests. Commits them to this repo. Forever.

This is NOT just scraping titles. Claude actually reads the content before forming opinions, which is more than most HN commenters do.

## Why This Exists

1. **Quota gaming** - Claude Code has a 5-hour quota reset timer. Running this 4x/day keeps it fresh.
2. **Entertainment** - AI hot takes on tech news are inherently funny
3. **Archive** - Permanent record of what an AI thought was interesting in 2025
4. **Because we can** - The best reason for any side project

## Quick Start

1. Fork this repo
2. Add the secrets (see below)
3. Enable GitHub Actions
4. Wait for the cron to trigger or run manually:
   ```bash
   gh workflow run "hn-digest.yml"
   ```

That's it. Claude handles the rest.

## How It Works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  cron 4x    │────▶│  fetch top  │────▶│  filter     │
│  daily      │     │  100 from   │     │  seen IDs   │
│             │     │  HN API     │     │  (24h)      │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │ 20 fresh
                    ┌─────────────┐     ┌──────▼──────┐
                    │  fetch      │◀────│  grab       │
                    │  article +  │     │  comments   │
                    │  comments   │     │  + previews │
                    └──────┬──────┘     └─────────────┘
                           │
┌─────────────┐     ┌──────▼──────┐     ┌─────────────┐
│  bark       │◀────│  claude     │────▶│  git commit │
│  notify     │     │  picks 5,   │     │  + issue    │
│             │     │  writes     │     │  + push     │
└─────────────┘     └─────────────┘     └─────────────┘
```

1. GitHub Actions cron fires 4x daily
2. Fetch top 100 stories from HN API
3. Light dedup: skip stories covered in last 24h (Claude does smart filtering)
4. Take first 20 unseen stories for evaluation
5. For each story: fetch HN comments (top 3) + article preview (top 3 stories only)
6. Claude reads `llms.txt` (memory index of all past digests)
7. Claude picks 5 fresh stories with good discussion
8. Claude writes digest JSON, converts to `digests/YYYY/MM/DD-HHMM.org` via skill scripts
9. Skill scripts regenerate `llms.txt` index and `index.html`
10. Git commit, push, create GitHub issue
11. Bark notification with spiciest comment quote
12. Quota timer resets as happy side effect

## Secrets You Need

| Secret | What | What Breaks Without It |
|--------|------|----------------------|
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code OAuth token | Everything. Claude can't run. |
| `CLAUDE_YOLO_APP_ID` | GitHub App ID | Can't commit or create issues. Run fails. |
| `CLAUDE_YOLO_APP_PRIVATE_KEY` | GitHub App private key | Same as above. |
| `BARK_SERVER` | Bark push notification server URL | Bark notification fails. Digest still works. |
| `BARK_DEVICES` | Bark device key(s) | Same. |
| `TG_BOT_TOKEN` | Telegram bot token (@BotFather) | TG notification fails. Optional. |
| `TG_CHANNEL_ID` | Telegram channel/chat ID | Same. |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL | Discord notification fails. Optional. |

Get the Claude token from: https://claude.com/settings/developer

The GitHub App needs: `contents:write`, `issues:write` permissions.

## Notification Channels

Digests are published to multiple channels:
- **GitHub Issues** - Always (required)
- **Bark** - iOS push notifications
- **Telegram** - Channel/group messages
- **Discord** - Webhook messages

Configure the secrets for the channels you want. Missing secrets = silent skip.

## File Structure

```
digests/
  2025/
    12/
      05-0900.org  ← digest from Dec 5, 09:00 UTC (org-mode format)
      05-1400.org
      ...
llms.txt                               ← auto-generated index Claude reads
.claude/skills/hn-digest/scripts/      ← converter and generation scripts
  json2org.py                          ← JSON -> org-mode conversion
  org2json.py                          ← org -> JSON (validation)
  org2html.py                          ← org -> HTML generation
  llms-gen.py                          ← regenerates llms.txt from digests/
```

## llms.txt Memory Index

Claude reads this before each run to avoid duplicates and understand past coverage.

Format:
```markdown
## Digests

- [2025-12-05 09:00](digests/2025/12/05-0900.md): Rust rewrites, $2M ARR, AI drama | 12345, 67890
- [2025-12-04 19:00](digests/2025/12/04-1900.md): Security fails, startup pivots | 11111, 22222
```

After writing each digest, Claude runs:
```bash
./.claude/skills/hn-digest/scripts/llms-gen.py  # scans digests/, rebuilds llms.txt
```

You can also manually add a single digest:
```bash
./.claude/skills/hn-digest/scripts/llms-gen.py --add digests/2025/12/05-0900.org
```

## Sample Output

See: [digests/2025/12/](digests/2025/12/) for real examples.

```markdown
# HN Digest 2025-12-05 09:00 UTC

> tech twitter energy but make it orange

**Highlights**
- Rust Rewrites: Memory safety is not a personality trait
- Solo $2M ARR: Luck disguised as a framework
- AI Replaces Team: Unemployment speedrun any%

---

### [Rust Rewrites Everything](https://example.com) • 847pts 423c
[HN discussion](https://news.ycombinator.com/item?id=12345)
TLDR: Company rewrote their monolith in Rust, claims 10x performance and 90% less memory.
Take: Another "we rewrote it in Rust" post. The team is now insufferable at parties.
Comment: "Memory safety is not a personality trait" -pragmaticdev

### [I Made $2M ARR as a Solo Founder](https://example.com) • 1203pts 567c
[HN discussion](https://news.ycombinator.com/item?id=12346)
TLDR: Founder shares 3-year journey from side project to $2M revenue SaaS.
Take: Translation: "I got lucky, here's a 47-step framework that had nothing to do with it."
Comment: "What stack did you use?" -every_hn_comment_ever

---
[archive](https://github.com/thevibeworks/claude-reads-hn)
```

## Local Testing

Manual trigger:
```bash
gh workflow run "hn-digest.yml"
```

With custom story count:
```bash
gh workflow run "hn-digest.yml" -f story_count=10
```

Test skill scripts:
```bash
# llms.txt generation
./.claude/skills/hn-digest/scripts/llms-gen.py -n              # dry run, print to stdout
./.claude/skills/hn-digest/scripts/llms-gen.py                 # regenerate llms.txt
./.claude/skills/hn-digest/scripts/llms-gen.py --add digests/2025/12/05-0900.org

# org-mode conversion
./.claude/skills/hn-digest/scripts/json2org.py /tmp/digest.json digests/2025/12/05-0900.org
./.claude/skills/hn-digest/scripts/org2json.py digests/2025/12/05-0900.org  # validate round-trip
./.claude/skills/hn-digest/scripts/org2html.py digests/**/*.org -o index.html
```

## What Can Go Wrong

**HN API is down**
- Workflow fails early, no digest created. Retry next run.

**All 100 stories were covered in last 24h**
- Unlikely. If it happens, Claude picks from the pool anyway.
- Worst case: digest has stories with "revisited" tag.

**Article fetch times out**
- Only fetches previews for top 3 stories with 8s timeout.
- If it fails, Claude just reads HN comments and title. TLDR might be vaguer.

**Bark notification fails**
- Non-fatal. Digest still gets created and committed.
- You just don't get the push notification.

**Claude hits rate limit**
- Shouldn't happen with 4x/day schedule, but if it does: run fails, retry next cycle.

**llms.txt gets huge**
- After ~1000 digests (~250 days), llms.txt will be large.
- Solution: Archive old entries, keep last 90 days in memory.
- Problem for future you. Hi, future you.

## FAQ

**Q: Isn't this a waste of AI tokens?**
A: It's called "entertainment" and "quota optimization". Also, you're reading this README, so clearly there's demand.

**Q: What if Claude's takes are bad?**
A: Then we have a permanent Git history of bad takes. Future AI historians will study this like we study old newspapers. "Look, this AI in 2025 thought cryptocurrency was dead. Again."

**Q: Can Claude be sued for defamation?**
A: Asking for a friend. But seriously, all takes are clearly labeled as AI-generated snark. If you take legal advice from a robot reading Hacker News, that's on you.

**Q: Why Hacker News specifically?**
A: Tech Twitter is too chaotic. Reddit is too long. HN is the Goldilocks zone of tech takes: just spicy enough, with actual discussion instead of dunks.

**Q: Why 4x per day and not continuous?**
A: Because the quota timer is 5 hours and HN's front page doesn't change THAT fast. Also, even Claude needs to sleep. (It doesn't, but let's pretend.)

**Q: Can I use this for other subreddits/forums?**
A: Sure. Fork it. Change the fetch script. Point Claude at different sources. The architecture is the same: fetch content → Claude reads → Claude writes → commit → notify.

## Infrastructure

### GitHub Pages (Frontend)

The site is served from this repo via GitHub Pages. Enable it in repo settings:
- Settings → Pages → Source: Deploy from branch (main, / root)
- Site: https://thevibeworks.github.io/claude-reads-hn

### Cloudflare Worker (Reliable Cron)

GitHub Actions cron is flaky. The CF Worker in `infra/cf-worker/` triggers workflows reliably:

```bash
cd infra/cf-worker
npm install
wrangler secret put GITHUB_TOKEN  # PAT with actions:write
wrangler deploy
```

Crons: 01:00, 06:00, 11:00, 16:00 UTC (same as GitHub Actions schedule)

## Related Projects

- [wake-up-claude](https://github.com/thevibeworks/wake-up-claude) - The OG quota poker, simple cron ping
- [claude-quota-scheduler](https://github.com/thevibeworks/claude-quota-scheduler) - The enterprise version with orchestration

## Disclaimer

```
All opinions in the digests are generated by an AI and do not represent
the views of anyone with actual judgment or legal liability.

If you're offended by a take, please remember:
1. It's an AI
2. It was specifically prompted to be spicy
3. Touch grass (both you and the AI)

No VCs were harmed in the making of this repository.
Some egos may have been bruised. That's a feature, not a bug.
```

---

*powered by [claude-code-action](https://github.com/anthropics/claude-code-action), poor life choices, and cron*
