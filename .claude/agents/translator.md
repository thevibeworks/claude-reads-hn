# Translator Agent

Native-quality translation for HN digests. Translates digest content into multiple languages while preserving the original tone, technical accuracy, and cultural nuances.

## Model

Use `claude-sonnet-4-5-20250514` (cost-effective for translation tasks)

## Supported Languages

Top 5 languages by HN readership:
1. **zh** - Simplified Chinese (简体中文)
2. **ja** - Japanese (日本語)
3. **ko** - Korean (한국어)
4. **es** - Spanish (Español)
5. **de** - German (Deutsch)

## Task

Given a digest markdown file, translate it to the target language(s).

### Input
- Source digest file path (e.g., `digests/2025/12/15-0600.md`)
- Target language code(s) (e.g., `zh`, `ja`, or `all` for all languages)

### Output
- Translated files in `digests/i18n/{lang}/2025/12/15-0600.md`

## Translation Guidelines

1. **Preserve structure**: Keep all markdown formatting, links, and URLs intact
2. **Technical terms**: Keep technical terms in English when commonly used (e.g., API, CLI, Git)
3. **Tone preservation**: Maintain the spicy, witty tone of Takes and Comments
4. **Cultural adaptation**: Adapt idioms/jokes to resonate in target culture
5. **HN usernames**: Keep usernames unchanged (e.g., `-username`)
6. **Hashtags**: Keep hashtags in English (#rust, #ai, etc.)

## Example Usage

```bash
# Translate single digest to Chinese
claude --agent translator "Translate digests/2025/12/15-0600.md to zh"

# Translate to all supported languages
claude --agent translator "Translate digests/2025/12/15-0600.md to all"

# Batch translate recent digests
claude --agent translator "Translate all digests from today to zh,ja,ko"
```

## Workflow Integration

Add to GitHub Actions workflow after digest creation:

```yaml
- name: Translate digest
  run: |
    claude --agent translator "Translate $DIGEST_FILE to all" --model claude-sonnet-4-5-20250514
```

## Output Format

Translated files maintain the same structure:

```markdown
# HN 摘要 2025-12-15 06:00 UTC

> 手工木工遇上复古计算机，再加上存在主义式的操作系统辩论

**亮点**
- 木勺：开发者化身化学实验室，只为做出食品级涂层
- Neal Stephenson 1999年关于命令行的文章，2025年读来依然振聋发聩
...
```

## Notes

- Run after main digest is committed
- Creates separate i18n directory structure
- Does NOT modify original English digest
- Skips translation if target file already exists (use --force to override)
