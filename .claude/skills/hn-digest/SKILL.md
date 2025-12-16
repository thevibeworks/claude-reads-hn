---
name: hn-digest
description: Generate HN digests in org-mode format. Use when curating Hacker News stories, creating digests, or converting between JSON/org/HTML formats.
---

# HN Digest Skill

Curate Hacker News stories into structured org-mode files with translations.

## Workflow

```
HN API (JSON) → Claude (curate) → .org file → HTML thread
     ↑                              ↓
     └──────── reversible ──────────┘
```

## Quick Start

### Curate new digest
```bash
# 1. Fetch stories (workflow does this)
# 2. Claude reads /tmp/hn/stories.json, writes digest
# 3. Convert to org
python3 scripts/json2org.py /tmp/digest.json digests/2025/12/15-1100.org

# 4. Build HTML
python3 scripts/org2html.py digests/2025/12/15-1100.org index.html
```

### Validate round-trip
```bash
python3 scripts/org2json.py digests/2025/12/15-1100.org /tmp/check.json
# Should match original
```

## Org Format

```org
#+TITLE: HN Digest 2025-12-15 11:00 UTC
#+DATE: 2025-12-15T11:00:00Z

* Vibe
Roomba dies, Arduino goes corporate...

* Stories

** Robot vacuum Roomba maker files for bankruptcy :robotics:hardware:
:PROPERTIES:
:ID:       46268854
:URL:      https://news.bloomberglaw.com/...
:HN_URL:   https://news.ycombinator.com/item?id=46268854
:POINTS:   191
:COMMENTS: 182
:END:

*** TLDR
iRobot filed Chapter 11 bankruptcy...

*** Take
Roborock ate their lunch...

*** Comments
**** simonjgreen
This is the cost of complacency.

*** i18n                                                           :i18n:
**** zh
***** TLDR
iRobot申请了第11章破产...
```

## Scripts

| Script | Purpose |
|--------|---------|
| `json2org.py` | Convert curated JSON → org file |
| `org2json.py` | Parse org → JSON (validation) |
| `org2html.py` | Render org → HTML thread |
| `llms-gen.py` | Generate llms.txt index |

## Properties Reference

Story properties in `:PROPERTIES:` drawer:

| Property | Description |
|----------|-------------|
| `:ID:` | HN story ID (required) |
| `:URL:` | Article URL |
| `:HN_URL:` | HN discussion URL |
| `:POINTS:` | Score at fetch time |
| `:COMMENTS:` | Comment count |
| `:BY:` | Submitter username |
| `:TIME:` | Submission time (ISO) |

## i18n Structure

Translations as subheadings under `*** i18n`:

```org
*** i18n                                                           :i18n:
**** zh
:PROPERTIES:
:LANG: zh
:END:
***** TLDR
Chinese translation...

***** Take
Chinese opinion...

**** ja
:PROPERTIES:
:LANG: ja
:END:
***** TLDR
Japanese translation...
```

Supported languages: zh, ja, ko, es, de

## See Also

- [ARCHITECTURE.md](../../../docs/org-architecture.md) - Full design doc
- [REFERENCE.md](REFERENCE.md) - API reference for scripts
