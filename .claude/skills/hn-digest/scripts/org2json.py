#!/usr/bin/env python3
"""
Parse org-mode HN digest back to JSON.

Usage:
    python3 org2json.py input.org output.json
    python3 org2json.py input.org  # outputs to stdout
"""

import json
import re
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Comment:
    by: str = ""
    text: str = ""
    id: Optional[int] = None


@dataclass
class I18nContent:
    tldr: str = ""
    take: str = ""


@dataclass
class Story:
    id: int = 0
    title: str = ""
    url: str = ""
    hn_url: str = ""
    points: int = 0
    comments_count: int = 0
    by: str = ""
    time: str = ""
    tldr: str = ""
    take: str = ""
    tags: list = field(default_factory=list)
    comments: list = field(default_factory=list)
    i18n: dict = field(default_factory=dict)


@dataclass
class Digest:
    date: str = ""
    vibe: str = ""
    highlights: list = field(default_factory=list)
    stories: list = field(default_factory=list)


def parse_properties(lines: list, start: int) -> tuple[dict, int]:
    """Parse :PROPERTIES: drawer, return props dict and end line index."""
    props = {}
    i = start

    if i >= len(lines) or not lines[i].strip().startswith(":PROPERTIES:"):
        return props, start

    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if line == ":END:":
            return props, i + 1

        match = re.match(r":(\w+):\s*(.+)", line)
        if match:
            key, value = match.groups()
            props[key.lower()] = value.strip()
        i += 1

    return props, i


def parse_tags(heading: str) -> list:
    """Extract tags from heading line."""
    match = re.search(r":[\w:]+:$", heading)
    if match:
        tags_str = match.group()
        return [t for t in tags_str.split(":") if t and t != "i18n"]
    return []


def clean_heading(heading: str) -> str:
    """Remove stars and tags from heading."""
    heading = re.sub(r"^\*+\s*", "", heading)
    heading = re.sub(r"\s*:[\w:]+:\s*$", "", heading)
    return heading.strip()


def get_heading_level(line: str) -> int:
    """Count leading stars."""
    match = re.match(r"^(\*+)", line)
    return len(match.group(1)) if match else 0


def collect_content(lines: list, start: int, stop_level: int) -> tuple[str, int]:
    """Collect content until next heading of same or higher level."""
    content = []
    i = start

    while i < len(lines):
        line = lines[i]
        level = get_heading_level(line)

        if level > 0 and level <= stop_level:
            break

        if not line.startswith(":"):
            content.append(line)
        i += 1

    return "\n".join(content).strip(), i


def parse_org(content: str) -> Digest:
    """Parse org content into Digest structure."""
    lines = content.split("\n")
    digest = Digest()

    for line in lines:
        if line.startswith("#+DATE:"):
            digest.date = line.split(":", 1)[1].strip()
        elif line.startswith("#+TITLE:"):
            pass

    i = 0
    current_story = None
    current_section = None
    current_i18n_lang = None

    while i < len(lines):
        line = lines[i]
        level = get_heading_level(line)

        if level == 0:
            i += 1
            continue

        heading = clean_heading(line)

        if level == 1:
            if heading == "Vibe":
                content, i = collect_content(lines, i + 1, 1)
                digest.vibe = content
                continue
            elif heading == "Highlights":
                i += 1
                while i < len(lines) and not lines[i].startswith("*"):
                    if lines[i].strip().startswith("- "):
                        digest.highlights.append(lines[i].strip()[2:])
                    i += 1
                continue
            elif heading == "Stories":
                i += 1
                continue

        elif level == 2:
            if current_story:
                digest.stories.append(current_story)

            current_story = Story()
            current_story.title = heading
            current_story.tags = parse_tags(line)

            props, i = parse_properties(lines, i + 1)
            if props:
                current_story.id = int(props.get("id", 0))
                current_story.url = props.get("url", "")
                current_story.hn_url = props.get("hn_url", "")
                current_story.points = int(props.get("points", 0))
                current_story.comments_count = int(props.get("comments", 0))
                current_story.by = props.get("by", "")
                current_story.time = props.get("time", "")
            continue

        elif level == 3 and current_story:
            current_section = heading.lower()
            current_i18n_lang = None

            if current_section == "tldr":
                content, i = collect_content(lines, i + 1, 3)
                current_story.tldr = content
                continue
            elif current_section == "take":
                content, i = collect_content(lines, i + 1, 3)
                current_story.take = content
                continue
            elif current_section == "comments":
                i += 1
                continue
            elif current_section == "i18n":
                i += 1
                continue

        elif level == 4:
            if current_section == "comments" and current_story:
                comment = Comment(by=heading)
                props, i = parse_properties(lines, i + 1)
                if props.get("comment_id"):
                    comment.id = int(props["comment_id"])
                content, i = collect_content(lines, i, 4)
                comment.text = content
                current_story.comments.append(comment)
                continue

            elif current_section == "i18n" and current_story:
                current_i18n_lang = heading.lower()
                props, i = parse_properties(lines, i + 1)
                if current_i18n_lang not in current_story.i18n:
                    current_story.i18n[current_i18n_lang] = I18nContent()
                continue

        elif level == 5 and current_i18n_lang and current_story:
            subsection = heading.lower()
            content, i = collect_content(lines, i + 1, 5)
            i18n_data = current_story.i18n.get(current_i18n_lang, I18nContent())

            if subsection == "tldr":
                i18n_data.tldr = content
            elif subsection == "take":
                i18n_data.take = content

            current_story.i18n[current_i18n_lang] = i18n_data
            continue

        i += 1

    if current_story:
        digest.stories.append(current_story)

    return digest


def digest_to_dict(digest: Digest) -> dict:
    """Convert Digest dataclass to JSON-serializable dict."""
    result = {
        "date": digest.date,
        "vibe": digest.vibe,
        "highlights": digest.highlights,
        "stories": []
    }

    for story in digest.stories:
        s = {
            "id": story.id,
            "title": story.title,
            "url": story.url,
            "hn_url": story.hn_url,
            "points": story.points,
            "comments_count": story.comments_count,
            "tldr": story.tldr,
            "take": story.take,
            "tags": story.tags,
            "comments": [{"by": c.by, "text": c.text, "id": c.id} for c in story.comments],
            "i18n": {lang: {"tldr": data.tldr, "take": data.take}
                     for lang, data in story.i18n.items()}
        }
        if story.by:
            s["by"] = story.by
        if story.time:
            s["time"] = story.time
        result["stories"].append(s)

    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: org2json.py input.org [output.json]", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    content = input_path.read_text()
    digest = parse_org(content)
    result = digest_to_dict(digest)

    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if output_path:
        output_path.write_text(json_output)
        print(f"Wrote {output_path}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
