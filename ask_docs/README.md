# Ask Docs — Document Q&A with Visual Citations

A Claude Code skill that parses your documents with [LiteParse](https://developers.llamaindex.ai/liteparse/), answers questions using the parsed text, and generates a self-contained HTML report with source citations — including bounding box highlights on the original page images.

![Ask Docs](assets/ask-docs.png)

## Install

```bash
npx skills add run-llama/liteparse_samples --skill ask_docs
```

Or manually:

```bash
cp -r ask_docs ~/.claude/skills/ask_docs
```

### Prerequisites

- Python 3.9+
- `pip install liteparse`
- Node 18+ with `npm i -g @llamaindex/liteparse`

## Usage

In Claude Code, run:

```
/ask-docs ./path/to/documents What are the key financial indicators?
```

This generates a timestamped HTML report in `ask_docs_output/` and opens it in your browser.

## How It Works

The skill orchestrates a 4-step pipeline:

1. **Parse** — LiteParse extracts text with bounding boxes from all supported files in the directory
2. **Read** — Claude reads the parsed text to understand all document content
3. **Answer** — Claude answers your question and extracts exact-quote citations from the source text
4. **Report** — A bundled Python script generates a self-contained HTML report with:
   - The synthesized answer
   - Source citation cards with page images and bounding box highlights
   - Parsed text with highlighted quotes
   - Optional PDF viewer toggle for each citation

## Supported File Formats

| Category | Formats |
|----------|---------|
| PDF | `.pdf` |
| Word | `.doc`, `.docx`, `.docm`, `.odt`, `.rtf` |
| PowerPoint | `.ppt`, `.pptx`, `.pptm`, `.odp` |
| Spreadsheets | `.xls`, `.xlsx`, `.xlsm`, `.ods`, `.csv`, `.tsv` |
| Images | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.webp`, `.svg` |
| Plaintext | `.txt`, `.md`, `.markdown`, `.rst` |

PDF files get full visual citations (page images + bounding box highlights). Plaintext files show highlighted text snippets.

Up to 50 files per run.

## Example Output

Open [`example_output/`](example_output/) to see a pre-generated report.

## Links

- [LiteParse Documentation](https://developers.llamaindex.ai/liteparse/)
- [Visual Citations Guide](https://developers.llamaindex.ai/liteparse/guides/visual-citations/)
- [LiteParse Agent Skill](https://developers.llamaindex.ai/liteparse/guides/agent-skill/)
