# Org-Mode Architecture for Claude Reads HN

## Vision

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌─────────────┐
│   HN API    │────▶│ Claude Agent │────▶│  .org file  │────▶│ HTML Thread │
│   (JSON)    │     │  (curator)   │     │ (archived)  │     │  (reader)   │
└─────────────┘     └──────────────┘     └─────────────┘     └─────────────┘
      ▲                                        │
      │                                        │
      └────────────────────────────────────────┘
              reversible / reproducible
```

**Key insight**: The org file is the single source of truth. It's:
- Human readable (plain text)
- Machine parseable (structured)
- Bidirectional (can reconstruct JSON or render HTML)
- Archive-friendly (git-able, diff-able)
- Self-documenting (metadata inline)

## Why Org-Mode?

| Feature | Markdown | Org-Mode |
|---------|----------|----------|
| Headings | `#` | `*` |
| Properties/metadata | YAML frontmatter (separate) | `:PROPERTIES:` drawer (inline) |
| IDs | None native | `:ID:` property |
| Tags | Hacked in (`#tag`) | Native `*heading :tag1:tag2:` |
| Folding/outline | Editor-dependent | Native |
| Links with IDs | `[text](url)` | `[[id:UUID][text]]` |
| Export | Many tools | Built-in to many formats |
| Checkboxes | `- [ ]` | `- [ ]` (same) |
| Tables | Pipe-based | Native with formulas |

**Org-mode gives us**:
- `:PROPERTIES:` drawers for metadata (story ID, URL, points, etc.)
- `:ID:` for unique anchoring
- Native tags (`:ai:opensource:rust:`)
- Structured hierarchy that maps to JSON naturally

## Proposed Org Format

```org
#+TITLE: HN Digest 2025-12-15 11:00 UTC
#+DATE: 2025-12-15T11:00:00Z
#+CURATOR: claude-opus-4.5
#+SOURCE: https://hacker-news.firebaseio.com/v0/

* Vibe
Roomba dies, Arduino goes corporate, and HN debates taxing our robot overlords

* Highlights
- Roomba: Chinese supplier inherits the throne after 35 years
- Hashcards: Plain-text flashcards for Anki haters
- JSDoc: You've been writing TypeScript all along
- Arduino: Open source until the lawyers show up
- AI Taxes: When your replacement also needs a W-2

* Stories

** Robot vacuum Roomba maker files for bankruptcy after 35 years :robotics:hardware:bankruptcy:
:PROPERTIES:
:ID:       46268854
:URL:      https://news.bloomberglaw.com/bankruptcy-law/robot-vacuum-roomba-maker-files-for-bankruptcy-after-35-years
:HN_URL:   https://news.ycombinator.com/item?id=46268854
:POINTS:   191
:COMMENTS: 182
:BY:       benrutter
:TIME:     2025-12-15T08:23:00Z
:END:

*** TLDR
iRobot, the MIT-founded company that invented robot vacuums, filed Chapter 11 bankruptcy
and is being taken over by its Chinese supplier Shenzhen PICEA Robotics.

*** Take
Roborock ate their lunch while iRobot kept selling the same overpriced hockey puck
with slightly better mapping. Being first to market means nothing if you refuse to iterate.

*** Comments

**** simonjgreen
:PROPERTIES:
:COMMENT_ID: 46269123
:END:
This is the cost of complacency. I tried Roborock and couldn't believe how much better it was.

**** furyg3
:PROPERTIES:
:COMMENT_ID: 46269456
:END:
Are there any good robo-vacuums that still clean your floor if the internet is down?

*** i18n                                                           :i18n:

**** zh
:PROPERTIES:
:LANG: zh
:END:
***** TLDR
iRobot这家发明扫地机器人的MIT衍生公司申请了第11章破产，被中国供应商深圳PICEA Robotics接管。

***** Take
Roborock抢了他们的饭碗，而iRobot还在卖同一个高价冰球。

**** ja
:PROPERTIES:
:LANG: ja
:END:
***** TLDR
ロボット掃除機を発明したMIT発のiRobotがChapter 11破産を申請。

***** Take
RoborockがiRobotの昼飯を奪った。


** Hashcards: A plain-text spaced repetition system :learning:tools:opensource:
:PROPERTIES:
:ID:       46264492
:URL:      https://borretti.me/article/hashcards-plain-text-spaced-repetition
:HN_URL:   https://news.ycombinator.com/item?id=46264492
:POINTS:   330
:COMMENTS: 147
:BY:       thunderbong
:TIME:     2025-12-15T06:12:00Z
:END:

*** TLDR
Hashcards stores flashcards as Markdown files, identifies them by content hash,
and uses SQLite for review history.

*** Take
Finally, flashcards for developers who spend more time configuring their tools
than actually learning.

*** Comments

**** btilly
:PROPERTIES:
:COMMENT_ID: 46265001
:END:
The real power of spaced repetition is behavior modification, not flashcards.

```

## Data Flow

### 1. HN API → JSON (raw fetch)

```json
{
  "id": 46268854,
  "title": "Robot vacuum Roomba maker files for bankruptcy after 35 years",
  "url": "https://news.bloomberglaw.com/...",
  "score": 191,
  "descendants": 182,
  "by": "benrutter",
  "time": 1734255780,
  "kids": [46269123, 46269456, ...]
}
```

### 2. Claude Agent → Curated JSON

```json
{
  "digest": {
    "date": "2025-12-15T11:00:00Z",
    "vibe": "Roomba dies, Arduino goes corporate...",
    "highlights": ["Roomba: Chinese supplier...", ...],
    "stories": [
      {
        "id": 46268854,
        "title": "Robot vacuum Roomba maker files for bankruptcy",
        "url": "https://...",
        "hn_url": "https://news.ycombinator.com/item?id=46268854",
        "points": 191,
        "comments_count": 182,
        "tldr": "iRobot filed Chapter 11...",
        "take": "Roborock ate their lunch...",
        "comments": [
          {"id": 46269123, "by": "simonjgreen", "text": "..."},
          ...
        ],
        "tags": ["robotics", "hardware", "bankruptcy"],
        "i18n": {
          "zh": {"tldr": "...", "take": "..."},
          "ja": {"tldr": "...", "take": "..."}
        }
      },
      ...
    ]
  }
}
```

### 3. JSON → Org (serialization)

Tool: `scripts/json2org.py`

```python
def story_to_org(story):
    tags = ':' + ':'.join(story['tags']) + ':'
    return f"""** {story['title']} {tags}
:PROPERTIES:
:ID:       {story['id']}
:URL:      {story['url']}
:HN_URL:   {story['hn_url']}
:POINTS:   {story['points']}
:COMMENTS: {story['comments_count']}
:END:

*** TLDR
{story['tldr']}

*** Take
{story['take']}

*** Comments
{''.join(comment_to_org(c) for c in story['comments'])}

*** i18n                                                           :i18n:
{''.join(i18n_to_org(lang, data) for lang, data in story['i18n'].items())}
"""
```

### 4. Org → JSON (deserialization)

Tool: `scripts/org2json.py`

Uses org-mode parser to reconstruct the JSON:
- Parse headings hierarchy
- Extract `:PROPERTIES:` drawers
- Map tags to array
- Reconstruct nested structure

This enables:
- **Validation**: Round-trip `json → org → json` should be identical
- **Editing**: Human can edit org file, changes propagate to JSON
- **Migration**: Import old markdown digests by converting to org

### 5. Org → HTML (rendering)

Tool: `scripts/org2html.py` or use existing parser (go-org, orgajs, mldoc)

Output: Thread-style HTML page with:
- Proper `id="46268854"` anchors
- Collapsible sections (using `<details>`)
- i18n toggle (show/hide translated content)
- Clean typography matching current design

## Directory Structure

```
claude-reads-hn/
├── digests/
│   └── 2025/
│       └── 12/
│           ├── 15-1100.org      # source of truth
│           └── 15-1100.json     # generated (optional cache)
├── scripts/
│   ├── json2org.py              # HN JSON → org
│   ├── org2json.py              # org → JSON (validation)
│   ├── org2html.py              # org → HTML
│   └── build.py                 # orchestrator
├── templates/
│   └── thread.html              # HTML template
├── index.html                   # generated static page
└── llms.txt                     # index (generated from org files)
```

## Workflow Integration

```yaml
# .github/workflows/hn-digest.yml

- name: fetch HN stories
  run: |
    # Fetch from HN API → /tmp/hn/stories.json

- name: let claude curate
  # Claude reads stories.json, writes digest.json with opinions + translations

- name: generate org file
  run: python3 scripts/json2org.py /tmp/digest.json digests/2025/12/15-1100.org

- name: validate (round-trip)
  run: |
    python3 scripts/org2json.py digests/2025/12/15-1100.org /tmp/validate.json
    diff /tmp/digest.json /tmp/validate.json

- name: build static page
  run: python3 scripts/build.py --all

- name: commit & push
  run: git add digests/ index.html && git commit && git push
```

## Parser Options

| Parser | Language | Pros | Cons |
|--------|----------|------|------|
| go-org | Go | Single binary, fast, has SSG | 80/20 subset |
| orgajs | JS | Full AST, unified ecosystem | Complex |
| mldoc | OCaml | Logseq's parser, handles md+org | OCaml dependency |
| org-ruby | Ruby | Mature | Ruby dependency |
| orgparse | Python | Native Python | Less maintained |
| pandoc | Haskell | Universal converter | Heavy, some org quirks |

**Recommendation**: Start with go-org for simplicity, or write custom Python parser for our subset.

## Benefits

1. **Single source of truth**: Org file is the canonical format
2. **Human readable**: Can be edited directly, reviewed in PRs
3. **Machine parseable**: Structured data extraction is trivial
4. **Bidirectional**: JSON ↔ Org ↔ HTML all lossless
5. **Archive friendly**: Plain text, git-able, grep-able
6. **Self-documenting**: Properties contain all metadata
7. **Future-proof**: Org-mode is a 20+ year old stable format
8. **i18n native**: Translations in subheadings, clean hierarchy

## Open Questions

1. **Parser choice**: Write custom or use existing?
2. **Build tool**: Python script vs static site generator (blorg)?
3. **Migration**: Convert existing 29 markdown digests to org?
4. **Caching**: Keep generated JSON alongside org, or regenerate on demand?
5. **Incremental builds**: Only rebuild changed digests?

## Next Steps

1. [ ] Write `json2org.py` - serialize curated JSON to org format
2. [ ] Write `org2json.py` - parse org back to JSON (validation)
3. [ ] Write `org2html.py` - render org to thread-style HTML
4. [ ] Convert one existing digest (15-1100.md) to org as proof of concept
5. [ ] Update workflow to generate org instead of markdown
6. [ ] Migrate remaining digests (optional, can coexist)

---

*This document is a living spec. Update as implementation progresses.*
