---
name: llms-txt
description: >
  Generate and update llms.txt memory index from digests. Use this skill when
  updating llms.txt after creating a digest, or regenerating the full index.
---

# llms.txt Generator

Fast generation of llms.txt from digest files.

## Usage

```bash
# Regenerate full llms.txt from all digests
./llms-gen.py

# Add single digest to llms.txt (prepend to ## Digests)
./llms-gen.py --add digests/2025/12/12-1554.md

# Dry run (print to stdout)
./llms-gen.py -n
```

## When to Use

- After creating a new digest, run `--add` with the new digest path
- To rebuild the full index, run without arguments
- The script scans digests/, extracts metadata, generates standard llms.txt format
