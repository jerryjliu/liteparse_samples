---
name: research-docs
description: Parse documents with LiteParse and answer questions with visual citations. Generates an HTML report with the answer, source page images, and bounding box highlights on cited text.
argument-hint: "[data_directory] [question]"
disable-model-invocation: true
allowed-tools: Bash(python *)
compatibility: Requires Python 3.9+, `pip install liteparse`, Node 18+, `npm i -g @llamaindex/liteparse`
---

# Research Docs — Document Q&A with Visual Citations

Parse documents with LiteParse, answer a question using the parsed text, and generate an HTML report with source citations highlighted on page images.

## Arguments

`$ARGUMENTS` should contain:
- **First argument (`$0`)**: Path to the data directory containing documents
- **Remaining arguments**: The question to answer

If either is missing, ask the user to provide them.

## Step 1 — Parse Documents

**IMPORTANT:** Always use the bundled Python script below for parsing. Do NOT call `lit` or `liteparse` CLI commands directly — use only `generate_report.py`.

Run the bundled parse script to extract text and bounding boxes from all supported files:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/generate_report.py" \
    --skill-dir "${CLAUDE_SKILL_DIR}" \
    --dir "$0" \
    --parse-only \
    --output /tmp/research_docs_parsed.json
```

This discovers and parses all supported files in the directory:
- **LiteParse formats**: PDF, DOCX, PPTX, XLSX, images (up to 50 files)
- **Plaintext**: .txt, .md, .rst (read directly)

The output is a JSON file with parsed text and bounding box coordinates for each page.

If the directory has more than 50 files and the user's question targets a specific document not in the first 50, re-run with a narrower `--dir` pointing to a subdirectory, or ask the user which files to focus on.

## Step 2 — Read Parsed Content

Read `/tmp/research_docs_parsed.json` using the Read tool. Focus on:
- Each file's `name` and `type`
- For LiteParse files: each page's `text` field (skip raw `textItems` — those are for bounding box rendering)
- For plaintext files: the `text` field
- The `summary` object for total counts

Build a mental model of all document content before answering.

## Step 3 — Answer with Citations

Using the parsed text as context, answer the user's question. Write your response as a JSON file:

```bash
cat > /tmp/research_docs_answer.json << 'ANSWER_EOF'
{
  "question": "<the user's question>",
  "answer": "<your answer in markdown with [N] citation markers>",
  "citations": [
    {
      "file": "<filename e.g. report.pdf>",
      "page": <1-indexed page number>,
      "quote": "<exact verbatim substring from the parsed text>",
      "relevance": "<explanation of what this value/quote means and how it supports the answer>"
    }
  ]
}
ANSWER_EOF
```

**Critical rules for the answer:**
- Embed **inline citation markers** like `[1]`, `[2]`, etc. in your answer text, corresponding to the **1-indexed** position in the `citations` array
- Place markers at the end of the sentence or claim they support
- Example: `"Reserve Bank credit totaled **$6,613,609 million** [1], with securities held outright at $6,375,679 million [2]."`

**Critical rules for what to cite:**
- **Cite the EVIDENCE, not just the label.** The user wants to audit your claims. If you say "revenue was $1.2B", cite the actual number `1,200,000` from the text — not just the heading "Revenue". You can cite both the value and the label if they're on the same page.
- **Cite specific data values** — numbers, percentages, dates, dollar amounts, quantities. These are what the user needs to verify.
- **Each `relevance` field should explain the "so what"** — not just restate the label but explain what this value means in context and how it supports your answer. E.g., instead of "Total revenue figure" write "Total revenue for Q3 2025, representing a 12% year-over-year increase that supports the growth trend discussed above."
- Include **5-15 citations** covering all key claims and data points in your answer.

**Critical rules for quote format:**
- `quote` MUST be **copied character-for-character** from the parsed text. It is used for bounding box lookup via exact string matching. Do NOT paraphrase, reword, clean up, or fix typos.
- **Prefer short, precise quotes** — a number like `6,613,609` or a short phrase like `Securities held outright` (under 60 characters). Shorter quotes match bounding boxes much more reliably than long sentences.
- If the text has unusual characters, hyphens, or formatting artifacts, include them exactly as they appear.
- `page` is **1-indexed** (matches LiteParse pageNum)
- `file` is just the filename (not the full path)
- For plaintext files (.txt, .md), set `page` to `0` (they have no pages)

## Step 4 — Generate HTML Report

Run the bundled script in generate mode to produce the visual report:

```bash
python "${CLAUDE_SKILL_DIR}/scripts/generate_report.py" \
    --skill-dir "${CLAUDE_SKILL_DIR}" \
    --dir "$0" \
    --answer-file /tmp/research_docs_answer.json \
    --output research_docs_output/
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
