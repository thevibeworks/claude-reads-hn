#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""
Add or update translations in digest JSON files.

This script works in two modes:
1. --check: Show what translations are missing
2. --apply: Apply translations from stdin JSON

Claude workflow:
  1. Run with --check to see what needs translation
  2. Claude generates translations
  3. Run with --apply to merge translations back

examples:
  %(prog)s digests/2025/12/27-1100.json --check              # Show missing
  %(prog)s digests/2025/12/27-1100.json --check --lang ko    # Check specific lang
  %(prog)s digests/2025/12/27-1100.json --apply < trans.json # Apply translations
"""

import argparse
import json
import sys
from pathlib import Path

SUPPORTED_LANGS = ["zh", "ja", "ko", "es", "de"]


def check_translations(digest: dict, langs: list[str]) -> dict:
    """Check what translations are missing. Returns structure for translation."""
    missing = {"meta": digest.get("meta", {}), "translations_needed": []}

    for story in digest.get("stories", []):
        story_id = story.get("id")
        title = story.get("title", "")
        content = story.get("content", {})
        i18n = story.get("i18n", {})

        story_missing = {
            "id": story_id,
            "title": title,
            "source": {
                "tldr": content.get("tldr", ""),
                "take": content.get("take", ""),
                "comments": [c.get("text", "") for c in content.get("comments", [])],
            },
            "missing_langs": [],
        }

        for lang in langs:
            lang_data = i18n.get(lang, {})
            source_comments = content.get("comments", [])
            lang_comments = lang_data.get("comments", [])

            # Check all fields: tldr, take required; comments count must match
            missing_fields = []
            if not lang_data.get("tldr"):
                missing_fields.append("tldr")
            if not lang_data.get("take"):
                missing_fields.append("take")
            if len(lang_comments) != len(source_comments):
                missing_fields.append(f"comments({len(lang_comments)}/{len(source_comments)})")

            if missing_fields:
                story_missing["missing_langs"].append(f"{lang}[{','.join(missing_fields)}]")

        if story_missing["missing_langs"]:
            missing["translations_needed"].append(story_missing)

    return missing


def apply_translations(digest: dict, translations: dict) -> dict:
    """Apply translations to digest. Returns updated digest."""
    trans_map = {t["id"]: t for t in translations.get("translations", [])}

    for story in digest.get("stories", []):
        story_id = story.get("id")
        if story_id not in trans_map:
            continue

        trans = trans_map[story_id]
        if "i18n" not in story:
            story["i18n"] = {}

        for lang, new_content in trans.get("i18n", {}).items():
            if lang not in story["i18n"]:
                story["i18n"][lang] = {}

            existing = story["i18n"][lang]

            # Merge: only fill missing fields, never overwrite existing
            for key in ["title", "tldr", "take"]:
                if key in new_content and new_content[key] and not existing.get(key):
                    existing[key] = new_content[key]

            # Comments: only fill if empty or count mismatch
            if "comments" in new_content and new_content["comments"]:
                if not existing.get("comments") or len(existing["comments"]) != len(new_content["comments"]):
                    existing["comments"] = new_content["comments"]

    return digest


def generate_translation_prompt(missing: dict) -> str:
    """Generate a prompt for Claude to translate."""
    if not missing["translations_needed"]:
        return "No translations needed."

    lines = ["Translate the following content:\n"]

    for story in missing["translations_needed"]:
        lines.append(f"## Story {story['id']}: {story['title']}")
        lines.append(f"Languages needed: {', '.join(story['missing_langs'])}\n")
        lines.append(f"TLDR (English): {story['source']['tldr']}")
        lines.append(f"Take (English): {story['source']['take']}")
        if story['source']['comments']:
            lines.append(f"Comments: {story['source']['comments']}")
        lines.append("")

    lines.append("\nRespond with JSON in this format:")
    lines.append("""```json
{
  "translations": [
    {
      "id": STORY_ID,
      "i18n": {
        "zh": {"tldr": "...", "take": "...", "comments": ["...", "..."]},
        "ja": {"tldr": "...", "take": "...", "comments": ["...", "..."]}
      }
    }
  ]
}
```""")

    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(
        description="Add translations to digest JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("file", help="Digest JSON file")
    p.add_argument("--check", action="store_true", help="Check missing translations")
    p.add_argument("--apply", action="store_true", help="Apply translations from stdin")
    p.add_argument("--lang", help="Comma-separated languages (default: all)")
    p.add_argument("--prompt", action="store_true", help="Generate translation prompt")
    p.add_argument("--json", action="store_true", help="Output as JSON (for --check)")
    args = p.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(1)

    digest = json.loads(path.read_text())
    langs = args.lang.split(",") if args.lang else SUPPORTED_LANGS

    if args.check or args.prompt:
        missing = check_translations(digest, langs)

        if args.prompt:
            print(generate_translation_prompt(missing))
        elif args.json:
            print(json.dumps(missing, indent=2))
        else:
            if not missing["translations_needed"]:
                print("All translations present for requested languages.")
            else:
                for story in missing["translations_needed"]:
                    print(f"Story {story['id']}: needs {', '.join(story['missing_langs'])}")

    elif args.apply:
        try:
            translations = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON from stdin: {e}", file=sys.stderr)
            sys.exit(1)

        updated = apply_translations(digest, translations)
        path.write_text(json.dumps(updated, indent=2, ensure_ascii=False))
        print(f"Updated {path}", file=sys.stderr)

    else:
        p.print_help()


if __name__ == "__main__":
    main()
