#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["jsonschema"]
# ///
"""
Validate HN digest JSON files against schema v2.0.

examples:
  %(prog)s digests/2025/12/27-1100.json           # Single file
  %(prog)s digests/**/*.json                       # All digests
  %(prog)s digests/2025/12/27-1100.json --strict   # Fail on warnings
"""

import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator, ValidationError

SCHEMA_PATH = Path(__file__).parent.parent.parent.parent.parent / "docs" / "schema-v2.json"


def load_schema() -> dict:
    """Load JSON schema from docs/schema-v2.json."""
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema not found at {SCHEMA_PATH}", file=sys.stderr)
        sys.exit(1)
    return json.loads(SCHEMA_PATH.read_text())


def validate_file(path: Path, schema: dict, strict: bool = False) -> tuple[bool, list[str]]:
    """Validate a single JSON file. Returns (valid, errors)."""
    errors = []
    warnings = []

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return False, [f"Invalid JSON: {e}"]

    validator = Draft7Validator(schema)
    for error in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        field = ".".join(str(p) for p in error.path) or "(root)"
        errors.append(f"{field}: {error.message}")

    # Additional semantic checks (warnings)
    if "stories" in data:
        ids = [s.get("id") for s in data["stories"]]
        if len(ids) != len(set(ids)):
            warnings.append("Duplicate story IDs detected")

        for i, story in enumerate(data["stories"]):
            if story.get("i18n") is None:
                warnings.append(f"stories[{i}]: Missing i18n field (should be empty object {{}})")

    if warnings:
        for w in warnings:
            print(f"  WARN: {w}", file=sys.stderr)
        if strict:
            errors.extend(warnings)

    return len(errors) == 0, errors


def main():
    p = argparse.ArgumentParser(
        description="Validate HN digest JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("files", nargs="+", help="JSON files to validate")
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    p.add_argument("--quiet", "-q", action="store_true", help="Only show errors")
    args = p.parse_args()

    schema = load_schema()
    total = 0
    failed = 0

    for pattern in args.files:
        for path in Path(".").glob(pattern) if "*" in pattern else [Path(pattern)]:
            if not path.exists():
                print(f"SKIP: {path} (not found)", file=sys.stderr)
                continue
            if not path.suffix == ".json":
                continue

            total += 1
            valid, errors = validate_file(path, schema, args.strict)

            if valid:
                if not args.quiet:
                    print(f"OK: {path}")
            else:
                failed += 1
                print(f"FAIL: {path}", file=sys.stderr)
                for err in errors:
                    print(f"  {err}", file=sys.stderr)

    print(f"\nValidated {total} files: {total - failed} passed, {failed} failed", file=sys.stderr)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
