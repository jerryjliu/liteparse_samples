---
name: ask-docs
description: Parse documents with LiteParse and answer questions with visual citations. Generates an HTML report with the answer, source page images, and bounding box highlights on cited text.
argument-hint: "[data_directory] [question]"
disable-model-invocation: true
allowed-tools: Bash(python *)
compatibility: Requires Python 3.9+, `pip install liteparse`, Node 18+, `npm i -g @llamaindex/liteparse`
---

# Ask Docs — Document Q&A with Visual Citations

Parse documents with LiteParse, answer a question using the parsed text, and generate an HTML report with source citations highlighted on page images.

## Arguments

`$ARGUMENTS` should contain:
- **First argument (`$0`)**: Path to the data directory containing documents
- **Remaining arguments**: The question to answer

If either is missing, ask the user to provide them.

## Step 1 — Parse Documents

Run the bundled parse script to extract text and bounding boxes from all supported files:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/generate_report.py" \
    --skill-dir "${CLAUDE_SKILL_DIR}" \
    --dir "$0" \
    --parse-only \
    --output /tmp/ask_docs_parsed.json
```

This discovers and parses all supported files in the directory:
- **LiteParse formats**: PDF, DOCX, PPTX, XLSX, images (up to 50 files)
- **Plaintext**: .txt, .md, .rst (read directly)

The output is a JSON file with parsed text and bounding box coordinates for each page.

## Step 2 — Read Parsed Content

Read `/tmp/ask_docs_parsed.json` using the Read tool. Focus on:
- Each file's `name` and `type`
- For LiteParse files: each page's `text` field (skip raw `textItems` — those are for bounding box rendering)
- For plaintext files: the `text` field
- The `summary` object for total counts

Build a mental model of all document content before answering.

## Step 3 — Answer with Citations

Using the parsed text as context, answer the user's question. Write your response as a JSON file:

```bash
cat > /tmp/ask_docs_answer.json << 'ANSWER_EOF'
{
  "question": "<the user's question>",
  "answer": "<your answer in markdown format>",
  "citations": [
    {
      "file": "<filename e.g. report.pdf>",
      "page": <1-indexed page number>,
      "quote": "<exact verbatim substring from the parsed text>",
      "relevance": "<1-sentence explanation of why this supports the answer>"
    }
  ]
}
ANSWER_EOF
```

**Critical rules for citations:**
- `quote` MUST be an **exact verbatim substring** copied from the parsed text. It will be used for bounding box lookup via exact string matching. Do not paraphrase or modify.
- `page` is **1-indexed** (matches LiteParse pageNum)
- `file` is just the filename (not the full path)
- Include **3-10 citations** covering the key evidence for your answer
- For plaintext files (.txt, .md), set `page` to `0` (they have no pages)
- Keep each `quote` short — a sentence or key phrase, not a full paragraph

## Step 4 — Generate HTML Report

Run the bundled script in generate mode to produce the visual report:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/generate_report.py" \
    --skill-dir "${CLAUDE_SKILL_DIR}" \
    --dir "$0" \
    --answer-file /tmp/ask_docs_answer.json \
    --output ask_docs_output/
```

This will:
1. Parse and screenshot only the cited pages (efficient — not all pages)
2. Find bounding boxes for each cited quote
3. Generate a self-contained HTML report with the answer, page images, and highlights
4. Open the report in the default browser

## Step 5 — Present Results

Tell the user:
1. Where the report was saved (the file path printed by the script)
2. A brief summary of the answer (2-3 sentences)
3. How many citations were found
