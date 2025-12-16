# HN Digest Script Reference

## json2org.py

Convert curated JSON to org-mode format.

### Usage
```bash
python3 json2org.py input.json output.org
python3 json2org.py input.json  # stdout
```

### Input JSON Schema
```json
{
  "date": "2025-12-15T11:00:00Z",
  "vibe": "One-line summary",
  "highlights": ["Story1 hook", "Story2 hook"],
  "stories": [
    {
      "id": 46268854,
      "title": "Story title",
      "url": "https://article.url",
      "hn_url": "https://news.ycombinator.com/item?id=46268854",
      "points": 191,
      "comments_count": 182,
      "by": "username",
      "time": "2025-12-15T08:23:00Z",
      "tldr": "Summary text",
      "take": "Opinion text",
      "tags": ["tag1", "tag2"],
      "comments": [
        {"by": "user", "text": "Comment", "id": 123}
      ],
      "i18n": {
        "zh": {"tldr": "Chinese", "take": "Chinese"},
        "ja": {"tldr": "Japanese", "take": "Japanese"}
      }
    }
  ]
}
```

---

## org2json.py

Parse org-mode digest back to JSON.

### Usage
```bash
python3 org2json.py input.org output.json
python3 org2json.py input.org  # stdout
```

### Parsing Rules
- `#+DATE:` → `date`
- `* Vibe` content → `vibe`
- `* Highlights` list items → `highlights[]`
- `** Heading :tags:` → story with `tags[]`
- `:PROPERTIES:` drawer → story metadata
- `*** TLDR/Take/Comments` → story content
- `*** i18n` subheadings → `i18n{}`

---

## org2html.py

Render org digests to HTML thread page.

### Usage
```bash
python3 org2html.py digests/*.org -o index.html
python3 org2html.py single.org  # stdout
```

### Features
- Dark/light theme toggle
- Language switcher (EN/ZH/JA)
- Story anchors by HN ID
- i18n text with `↳` prefix

---

## llms-gen.py

Generate llms.txt index from digest files.

### Usage
```bash
./llms-gen.py  # scans digests/, writes llms.txt
```

### Output Format
```
# Claude Reads HN

> Description

## Digests

- [2025-12-15 11:00](digests/2025/12/15-1100.org): Title | story_ids
```

---

## Round-Trip Validation

```bash
# Convert JSON → org → JSON and compare
python3 json2org.py input.json /tmp/test.org
python3 org2json.py /tmp/test.org /tmp/roundtrip.json
diff input.json /tmp/roundtrip.json
```

Fields preserved:
- ✅ date, vibe, highlights
- ✅ story: id, title, url, hn_url, points, comments_count, by, time
- ✅ story: tldr, take, tags, comments
- ✅ i18n translations (zh, ja, ko, es, de)

---

## Data Flow

```
HN API
   │
   ▼
/tmp/hn/stories.json    ← workflow fetches
   │
   ▼
Claude agent            ← curates, adds opinions + i18n
   │
   ▼
/tmp/digest.json        ← curated output
   │
   ▼
json2org.py
   │
   ▼
digests/2025/12/15-1100.org   ← archived source of truth
   │
   ├──▶ org2json.py → validate round-trip
   │
   └──▶ org2html.py → index.html (static page)
```
