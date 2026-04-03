#!/usr/bin/env python3
"""
LiteParse Ask Docs — Report Generator

Two modes:
  --parse-only : Discover and parse all supported files in a directory, output JSON
  --answer-file: Generate an HTML report from an answer JSON file with visual citations
"""

import argparse
import base64
import html as html_module
import json
import os
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

LITEPARSE_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".docm", ".odt", ".rtf",
    ".ppt", ".pptx", ".pptm", ".odp",
    ".xls", ".xlsx", ".xlsm", ".ods", ".csv", ".tsv",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp", ".svg",
}
PLAINTEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".rst", ".text"}


# ── File Discovery ────────────────────────────────────────────────────

def discover_files(data_dir: Path, max_files: int):
    """Discover supported files in a directory. Returns (liteparse_files, plaintext_files)."""
    liteparse_files = []
    plaintext_files = []

    if not data_dir.is_dir():
        print(f"Error: {data_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    for f in sorted(data_dir.iterdir()):
        if not f.is_file():
            continue
        ext = f.suffix.lower()
        if ext in LITEPARSE_EXTENSIONS:
            liteparse_files.append(f)
        elif ext in PLAINTEXT_EXTENSIONS:
            plaintext_files.append(f)

    total = len(liteparse_files) + len(plaintext_files)
    if total > max_files:
        print(f"Warning: Found {total} files, capping at {max_files}", file=sys.stderr)
        # Prioritize liteparse files, then plaintext
        remaining = max_files
        if len(liteparse_files) > remaining:
            liteparse_files = liteparse_files[:remaining]
            plaintext_files = []
        else:
            remaining -= len(liteparse_files)
            plaintext_files = plaintext_files[:remaining]

    return liteparse_files, plaintext_files


# ── Parse-Only Mode ──────────────────────────────────────────────────

def run_parse_only(args):
    """Parse all files and output structured JSON."""
    from liteparse import LiteParse

    data_dir = Path(args.dir)
    liteparse_files, plaintext_files = discover_files(data_dir, args.max_files)

    if not liteparse_files and not plaintext_files:
        print(f"Error: No supported files found in {data_dir}", file=sys.stderr)
        sys.exit(1)

    parser = LiteParse()
    files_data = []
    total_pages = 0

    # Parse LiteParse-supported files
    for filepath in liteparse_files:
        print(f"Parsing: {filepath.name}...", file=sys.stderr, end=" ", flush=True)
        t0 = time.perf_counter()
        try:
            result = parser.parse(str(filepath), dpi=args.dpi)
        except Exception as e:
            print(f"FAILED ({e})", file=sys.stderr)
            continue
        elapsed = time.perf_counter() - t0

        pages_data = []
        for page in result.pages:
            text_items = []
            for item in page.textItems:
                text_items.append({
                    "text": item.text,
                    "x": item.x,
                    "y": item.y,
                    "width": item.width,
                    "height": item.height,
                })
            pages_data.append({
                "pageNum": page.pageNum,
                "width": page.width,
                "height": page.height,
                "text": page.text,
                "textItems": text_items,
            })

        total_pages += len(pages_data)
        files_data.append({
            "name": filepath.name,
            "path": str(filepath),
            "type": "liteparse",
            "parseTime": round(elapsed, 3),
            "pages": pages_data,
        })
        print(f"done in {elapsed:.2f}s ({len(pages_data)} pages)", file=sys.stderr)

    # Read plaintext files
    for filepath in plaintext_files:
        print(f"Reading: {filepath.name}...", file=sys.stderr, end=" ", flush=True)
        try:
            text = filepath.read_text(errors="replace")
        except Exception as e:
            print(f"FAILED ({e})", file=sys.stderr)
            continue
        files_data.append({
            "name": filepath.name,
            "path": str(filepath),
            "type": "plaintext",
            "text": text,
        })
        print("done", file=sys.stderr)

    output_data = {
        "data_dir": str(data_dir),
        "files": files_data,
        "summary": {
            "total_files": len(files_data),
            "total_pages": total_pages,
            "liteparse_files": sum(1 for f in files_data if f["type"] == "liteparse"),
            "plaintext_files": sum(1 for f in files_data if f["type"] == "plaintext"),
        },
    }

    output_json = json.dumps(output_data, ensure_ascii=False)

    if args.output == "-":
        print(output_json)
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json)
        print(f"\nParsed JSON written to {output_path}", file=sys.stderr)
        print(f"Summary: {output_data['summary']}", file=sys.stderr)


# ── Markdown to HTML ─────────────────────────────────────────────────

def markdown_to_html(text):
    """Simple markdown to HTML conversion (no external deps)."""
    lines = text.split("\n")
    html_parts = []
    in_list = None  # "ul" or "ol"
    in_paragraph = False

    for line in lines:
        stripped = line.strip()

        # Close list if current line isn't a list item
        if in_list and not re.match(r"^[-*]\s", stripped) and not re.match(r"^\d+\.\s", stripped):
            html_parts.append(f"</{in_list}>")
            in_list = None

        # Empty line — close paragraph
        if not stripped:
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            continue

        # Headers
        m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if m:
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            level = len(m.group(1))
            content = _inline_markdown(html_module.escape(m.group(2)))
            html_parts.append(f"<h{level}>{content}</h{level}>")
            continue

        # Unordered list
        m = re.match(r"^[-*]\s+(.+)$", stripped)
        if m:
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            if in_list != "ul":
                if in_list:
                    html_parts.append(f"</{in_list}>")
                html_parts.append("<ul>")
                in_list = "ul"
            content = _inline_markdown(html_module.escape(m.group(1)))
            html_parts.append(f"<li>{content}</li>")
            continue

        # Ordered list
        m = re.match(r"^\d+\.\s+(.+)$", stripped)
        if m:
            if in_paragraph:
                html_parts.append("</p>")
                in_paragraph = False
            if in_list != "ol":
                if in_list:
                    html_parts.append(f"</{in_list}>")
                html_parts.append("<ol>")
                in_list = "ol"
            content = _inline_markdown(html_module.escape(m.group(1)))
            html_parts.append(f"<li>{content}</li>")
            continue

        # Regular text — paragraph
        escaped = html_module.escape(stripped)
        content = _inline_markdown(escaped)
        if not in_paragraph:
            html_parts.append("<p>")
            in_paragraph = True
        else:
            html_parts.append(" ")
        html_parts.append(content)

    # Close open elements
    if in_paragraph:
        html_parts.append("</p>")
    if in_list:
        html_parts.append(f"</{in_list}>")

    return "\n".join(html_parts)


def _inline_markdown(text):
    """Convert inline markdown: bold, italic, code."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    return text


# ── Generate Mode ────────────────────────────────────────────────────

def run_generate(args):
    """Generate HTML report from answer JSON."""
    from liteparse import LiteParse

    # Load answer JSON
    answer_data = json.loads(Path(args.answer_file).read_text())
    question = answer_data["question"]
    answer_text = answer_data["answer"]
    citations = answer_data["citations"]

    data_dir = Path(args.dir)
    parser = LiteParse()
    dpi = args.dpi
    scale = dpi / 72

    # Deduplicate: group citations by (file, page) to avoid re-parsing
    page_cache = {}  # (file, page) -> {page_data, img_b64}

    print(f"Processing {len(citations)} citations...", file=sys.stderr)

    for cit in citations:
        filename = cit["file"]
        page_num = cit.get("page", 0)
        cache_key = (filename, page_num)

        if cache_key in page_cache or page_num == 0:
            continue

        filepath = data_dir / filename
        if not filepath.exists():
            print(f"  Warning: {filepath} not found, skipping", file=sys.stderr)
            continue

        page_str = str(page_num)
        print(f"  Parsing {filename} page {page_num}...", file=sys.stderr, end=" ", flush=True)

        try:
            result = parser.parse(str(filepath), target_pages=page_str, dpi=dpi)
            screenshots = parser.screenshot(
                str(filepath), target_pages=page_str, dpi=dpi, load_bytes=True
            )
        except Exception as e:
            print(f"FAILED ({e})", file=sys.stderr)
            continue

        if not result.pages:
            print("no pages returned", file=sys.stderr)
            continue

        page = result.pages[0]
        shot = next(
            (s for s in screenshots.screenshots if s.page_num == page.pageNum), None
        )
        img_b64 = ""
        if shot and shot.image_bytes:
            img_b64 = base64.b64encode(shot.image_bytes).decode()

        text_items = []
        for item in page.textItems:
            text_items.append({
                "text": item.text,
                "x": item.x,
                "y": item.y,
                "width": item.width,
                "height": item.height,
            })

        page_cache[cache_key] = {
            "pageWidth": page.width,
            "pageHeight": page.height,
            "textItems": text_items,
            "image": img_b64,
            "pageText": page.text,
        }
        print("done", file=sys.stderr)

    # Build citation data for the template
    citation_data = []
    for i, cit in enumerate(citations):
        filename = cit["file"]
        page_num = cit.get("page", 0)
        cache_key = (filename, page_num)

        if page_num == 0:
            # Plaintext citation
            filepath = data_dir / filename
            file_text = ""
            if filepath.exists():
                try:
                    file_text = filepath.read_text(errors="replace")
                except Exception:
                    pass
            citation_data.append({
                "file": filename,
                "page": 0,
                "quote": cit["quote"],
                "relevance": cit.get("relevance", ""),
                "type": "plaintext",
                "pageText": file_text,
            })
        elif cache_key in page_cache:
            cached = page_cache[cache_key]
            citation_data.append({
                "file": filename,
                "page": page_num,
                "quote": cit["quote"],
                "relevance": cit.get("relevance", ""),
                "type": "liteparse",
                "pageWidth": cached["pageWidth"],
                "pageHeight": cached["pageHeight"],
                "textItems": cached["textItems"],
                "pageText": cached["pageText"],
                "image": cached["image"],
            })
        else:
            # File not found or parse failed — show as text-only
            citation_data.append({
                "file": filename,
                "page": page_num,
                "quote": cit["quote"],
                "relevance": cit.get("relevance", ""),
                "type": "text-only",
                "pageText": "",
            })

    # Compute relative path from output dir to data dir (for PDF viewer iframes)
    output_dir = Path(args.output).resolve()
    data_dir_resolved = data_dir.resolve()
    try:
        rel_data = os.path.relpath(data_dir_resolved, output_dir)
    except ValueError:
        rel_data = str(data_dir_resolved)  # fallback for cross-drive on Windows

    # Build hidden image tags and slim citation JSON
    images_html_parts = []
    citations_json = []
    for i, cit in enumerate(citation_data):
        img_id = None
        if cit.get("image"):
            img_id = f"cite-img-{i}"
            images_html_parts.append(
                f'<img id="{img_id}" class="hidden-img" '
                f'src="data:image/png;base64,{cit["image"]}" />'
            )
        slim = {k: v for k, v in cit.items() if k != "image"}
        slim["imgId"] = img_id
        # Add relative PDF path for the PDF viewer toggle
        if cit["type"] == "liteparse" and cit["file"].lower().endswith(".pdf"):
            slim["pdfPath"] = f"{rel_data}/{cit['file']}"
        citations_json.append(slim)

    # Count unique docs and pages
    unique_docs = set()
    unique_pages = set()
    for cit in citation_data:
        unique_docs.add(cit["file"])
        if cit["page"] > 0:
            unique_pages.add((cit["file"], cit["page"]))

    # Render answer to HTML
    answer_html = markdown_to_html(answer_text)

    # Load and fill template
    template_path = Path(args.skill_dir) / "templates" / "report.html"
    if not template_path.exists():
        print(f"Error: Template not found at {template_path}", file=sys.stderr)
        sys.exit(1)

    template = template_path.read_text()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_out = template
    html_out = html_out.replace("{{QUESTION}}", html_module.escape(question))
    html_out = html_out.replace("{{ANSWER_HTML}}", answer_html)
    html_out = html_out.replace("{{TIMESTAMP}}", timestamp)
    html_out = html_out.replace("{{NUM_DOCS}}", str(len(unique_docs)))
    html_out = html_out.replace("{{NUM_PAGES}}", str(len(unique_pages)))
    html_out = html_out.replace("{{NUM_CITATIONS}}", str(len(citations_json)))
    html_out = html_out.replace("{{CITATIONS_JSON}}", json.dumps(citations_json))
    html_out = html_out.replace("{{IMAGES_HTML}}", "\n".join(images_html_parts))
    html_out = html_out.replace("{{DPI}}", str(dpi))

    # Write output
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = f"report-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.html"
    output_path = output_dir / filename
    output_path.write_text(html_out)

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(f"\nReport written to {output_path.resolve()}", file=sys.stderr)
    print(f"Size: {size_mb:.1f} MB | Citations: {len(citations_json)}", file=sys.stderr)

    # Open in browser
    webbrowser.open(f"file://{output_path.resolve()}")
    # Also print path to stdout for Claude to read
    print(str(output_path.resolve()))


# ── Main ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="LiteParse Ask Docs — Report Generator"
    )
    ap.add_argument("--skill-dir", required=True,
                    help="Path to skill directory (for templates)")
    ap.add_argument("--dir", required=True,
                    help="Data directory containing documents")
    ap.add_argument("--parse-only", action="store_true",
                    help="Parse docs and output JSON only")
    ap.add_argument("--answer-file",
                    help="Path to answer JSON (for generate mode)")
    ap.add_argument("--output", default="ask_docs_output/",
                    help="Output path (file for --parse-only, directory for generate)")
    ap.add_argument("--dpi", type=int, default=150,
                    help="DPI for screenshots (default: 150)")
    ap.add_argument("--max-files", type=int, default=50,
                    help="Maximum files to process (default: 50)")
    args = ap.parse_args()

    if args.parse_only:
        run_parse_only(args)
    elif args.answer_file:
        run_generate(args)
    else:
        print("Error: Specify --parse-only or --answer-file", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
