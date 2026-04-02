"""
LiteParse vs PyPDF vs PyMuPDF — Table Extraction Comparison Demo

Parses real-world government/finance/healthcare PDFs and renders
a side-by-side HTML comparison with original page screenshots.

Configuration: edit docs.json to add/remove documents and pages.
"""

import html
import json
import time
from pathlib import Path

import fitz  # PyMuPDF
import pypdf
from liteparse import LiteParse

# ── Config ──────────────────────────────────────────────────────────────
DATA_DIR = Path("../data")
OUTPUT_DIR = Path("output")

with open("docs.json") as f:
    DOCS_CONFIG = json.load(f)


# ── Parsers ─────────────────────────────────────────────────────────────
def parse_with_liteparse(filepath: str, pages: list[int]) -> tuple[str, float]:
    page_str = ",".join(str(p + 1) for p in pages)
    parser = LiteParse()
    t0 = time.perf_counter()
    result = parser.parse(filepath, target_pages=page_str)
    elapsed = time.perf_counter() - t0
    return result.text, elapsed


def parse_with_pypdf(filepath: str, pages: list[int]) -> tuple[str, float]:
    t0 = time.perf_counter()
    reader = pypdf.PdfReader(filepath)
    texts = []
    for p in pages:
        if p < len(reader.pages):
            texts.append(reader.pages[p].extract_text() or "")
    elapsed = time.perf_counter() - t0
    return "\n\n".join(texts), elapsed


def parse_with_pymupdf(filepath: str, pages: list[int]) -> tuple[str, float]:
    t0 = time.perf_counter()
    doc = fitz.open(filepath)
    texts = []
    for p in pages:
        if p < len(doc):
            texts.append(doc[p].get_text())
    doc.close()
    elapsed = time.perf_counter() - t0
    return "\n\n".join(texts), elapsed


# ── Run all parsers ─────────────────────────────────────────────────────
print("Parsing documents...")
results = {}
for cfg in DOCS_CONFIG:
    name = cfg["name"]
    filepath = str(DATA_DIR / cfg["file"])
    print(f"  -> {name}")
    lp_text, lp_time = parse_with_liteparse(filepath, cfg["pages"])
    pp_text, pp_time = parse_with_pypdf(filepath, cfg["pages"])
    pm_text, pm_time = parse_with_pymupdf(filepath, cfg["pages"])

    results[name] = {
        "cfg": cfg,
        "liteparse": {"text": lp_text, "time": lp_time},
        "pypdf": {"text": pp_text, "time": pp_time},
        "pymupdf": {"text": pm_text, "time": pm_time},
    }
    print(f"    LiteParse: {lp_time:.2f}s | PyPDF: {pp_time:.2f}s | PyMuPDF: {pm_time:.2f}s")


# ── Compute summary stats ──────────────────────────────────────────────
total_lp = sum(d["liteparse"]["time"] for d in results.values())
total_pp = sum(d["pypdf"]["time"] for d in results.values())
total_pm = sum(d["pymupdf"]["time"] for d in results.values())
num_docs = len(results)
total_pages = sum(len(d["cfg"]["pages"]) for d in results.values())


# ── Generate HTML ───────────────────────────────────────────────────────
def esc(s: str) -> str:
    return html.escape(s)


doc_sections = []
parsers = [
    ("liteparse", "#3E18F9", "LiteParse"),
    ("pypdf", "#4B72FE", "PyPDF"),
    ("pymupdf", "#FF8705", "PyMuPDF"),
]
for idx, (name, data) in enumerate(results.items()):
    cfg = data["cfg"]
    page_label = ", ".join(str(p + 1) for p in cfg["pages"])

    # PDF iframe — path relative to output/ HTML file (../../data/...)
    first_page = cfg["pages"][0] + 1
    pdf_html_path = f"../../data/{cfg['file']}#page={first_page}"
    pdf_iframe = f'<iframe class="pdf-iframe" src="{pdf_html_path}"></iframe>'

    # Build tabs and tab content
    tab_buttons = ""
    tab_panes = ""
    for ti, (parser_name, color, label) in enumerate(parsers):
        d = data[parser_name]
        active = " active" if ti == 0 else ""
        tab_buttons += f'<button class="tab-btn{active}" data-tab="doc{idx}-{parser_name}" style="--tab-color: {color}">{label} <span class="tab-time">{d["time"]:.3f}s</span></button>'
        tab_panes += f'<pre class="tab-pane{active}" id="doc{idx}-{parser_name}">{esc(d["text"])}</pre>'

    doc_sections.append(f"""
    <div class="doc-card" id="doc-{idx}">
      <div class="doc-header">
        <h2>{esc(name)}</h2>
        <div class="doc-meta">
          <span class="meta-tag">Pages {page_label}</span>
          <span class="meta-tag">{esc(cfg['source'])}</span>
        </div>
        <p class="doc-desc">{esc(cfg['desc'])}</p>
      </div>
      <div class="doc-body">
        <div class="pdf-viewer">
          <div class="viewer-label">Original PDF &mdash; Pages {page_label}</div>
          {pdf_iframe}
        </div>
        <div class="output-section">
          <div class="tab-bar">{tab_buttons}</div>
          <div class="tab-content">{tab_panes}</div>
        </div>
      </div>
    </div>""")


html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LiteParse vs PyPDF vs PyMuPDF — Table Extraction Comparison</title>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<link href="https://cdn.jsdelivr.net/fontsource/fonts/overused-grotesk@latest/latin.css" rel="stylesheet">
<style>
  :root {{
    --bg: #FFFFFF;
    --bg-alt: #F5F5F5;
    --surface: #FFFFFF;
    --surface2: #F5F5F5;
    --surface3: #EBEBEB;
    --surface-dark: #1F1F1F;
    --border: #E7E7E7;
    --text: #000000;
    --text-dim: #737373;
    --purple: #3E18F9;
    --purple-mid: #4B72FE;
    --purple-light: #92AEFF;
    --orange: #FF8705;
    --pink: #FF8DF2;
    --blue: #37D7FA;
    --gradient-brand: linear-gradient(148.35deg, #37d7fa -.08%, #4b72fe 39.93%, #ff8df2 67.94%, #ff8705 99.94%);
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Overused Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
  }}

  /* Hero */
  .hero {{
    text-align: center;
    padding: 3.5rem 2rem 2.5rem;
    background: linear-gradient(180deg, rgba(62,24,249,0.04) 0%, transparent 70%);
    border-bottom: 1px solid var(--border);
  }}
  .hero h1 {{ font-size: 2.8rem; font-weight: 500; letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 0.6rem; }}
  .hero h1 .accent {{ color: var(--purple); }}
  .hero h1 .dim {{ color: var(--text-dim); font-weight: 400; }}
  .hero .subtitle {{ color: var(--text-dim); font-size: 1.1rem; max-width: 680px; margin: 0 auto 1.5rem; }}
  .badge-row {{ display: flex; gap: 0.6rem; justify-content: center; flex-wrap: wrap; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 0.3rem;
    background: var(--bg-alt); border: 1px solid var(--border);
    border-radius: 9999px; padding: 0.3rem 0.8rem; font-size: 0.82rem; color: var(--text-dim);
  }}
  .badge strong {{ color: var(--purple); font-weight: 600; }}
  .stats-bar {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    max-width: 800px; margin: 2rem auto 0; gap: 1px;
    background: var(--border); border-radius: 12px; overflow: hidden;
  }}
  .stat {{ background: var(--bg); padding: 1rem; text-align: center; }}
  .stat .val {{ font-size: 1.5rem; font-weight: 500; color: var(--purple); font-variant-numeric: tabular-nums; letter-spacing: -0.03em; }}
  .stat .lbl {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.04em; margin-top: 0.15rem;
  }}

  .container {{ max-width: 1500px; margin: 0 auto; padding: 2rem 1.5rem 4rem; }}

  /* Nav */
  .doc-nav {{
    display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 2rem;
    padding: 1rem; background: var(--bg-alt); border-radius: 12px; border: 1px solid var(--border);
  }}
  .doc-nav a {{
    color: var(--text-dim); text-decoration: none; font-size: 0.8rem;
    padding: 0.3rem 0.7rem; border-radius: 6px; transition: all 0.15s;
  }}
  .doc-nav a:hover {{ background: var(--surface3); color: var(--text); }}

  /* Document card */
  .doc-card {{
    background: var(--bg); border-radius: 16px;
    border: 1px solid var(--border); margin-bottom: 2.5rem; overflow: hidden;
  }}
  .doc-header {{ padding: 1.5rem 2rem 1rem; }}
  .doc-header h2 {{ font-size: 1.25rem; font-weight: 500; letter-spacing: -0.03em; margin-bottom: 0.4rem; }}
  .doc-meta {{ display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 0.4rem; }}
  .meta-tag {{
    font-family: 'IBM Plex Mono', monospace;
    background: var(--bg-alt); border-radius: 6px; padding: 0.15rem 0.5rem; font-size: 0.7rem; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.02em;
  }}
  .doc-desc {{ color: var(--text-dim); font-size: 0.88rem; }}

  /* Two-column body: PDF viewer + tabbed output */
  .doc-body {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    border-top: 1px solid var(--border);
    min-height: 700px;
  }}

  /* PDF viewer (left) */
  .pdf-viewer {{
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    background: var(--bg-alt);
  }}
  .viewer-label {{
    font-family: 'IBM Plex Mono', monospace;
    padding: 0.5rem 1rem;
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text-dim);
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
    flex-shrink: 0;
  }}
  .pdf-iframe {{
    flex: 1;
    width: 100%;
    border: none;
    min-height: 700px;
  }}

  /* Tabbed output (right) */
  .output-section {{
    display: flex;
    flex-direction: column;
  }}
  .tab-bar {{
    display: flex;
    gap: 0;
    background: var(--bg);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
  }}
  .tab-btn {{
    padding: 0.6rem 1.2rem;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--text-dim);
    background: transparent;
    border: none;
    border-bottom: 3px solid transparent;
    cursor: pointer;
    transition: all 0.15s;
    font-family: inherit;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }}
  .tab-btn:hover {{ color: var(--text); background: var(--bg-alt); }}
  .tab-btn.active {{
    color: var(--text);
    border-bottom-color: var(--tab-color);
    background: var(--bg-alt);
  }}
  .tab-time {{
    font-size: 0.7rem;
    font-weight: 400;
    color: var(--text-dim);
    font-family: 'IBM Plex Mono', monospace;
    font-variant-numeric: tabular-nums;
  }}
  .tab-content {{
    flex: 1;
    position: relative;
    overflow: hidden;
  }}
  .tab-pane {{
    display: none;
    position: absolute;
    inset: 0;
    margin: 0;
    padding: 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    line-height: 1.55;
    white-space: pre;
    overflow: auto;
    color: var(--text);
    background: var(--bg-alt);
    tab-size: 4;
  }}
  .tab-pane.active {{ display: block; }}
  .tab-pane::-webkit-scrollbar {{ width: 6px; height: 6px; }}
  .tab-pane::-webkit-scrollbar-track {{ background: transparent; }}
  .tab-pane::-webkit-scrollbar-thumb {{ background: var(--surface3); border-radius: 3px; }}

  /* Footer */
  .footer {{
    text-align: center; padding: 2.5rem 2rem;
    color: var(--text-dim); font-size: 0.85rem; border-top: 1px solid var(--border);
  }}
  .footer a {{ color: var(--purple); text-decoration: none; }}
  .footer a:hover {{ text-decoration: underline; }}
  .footer .install {{
    display: inline-block; background: var(--bg-alt); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.4rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.9rem; margin-top: 0.8rem; color: var(--purple);
  }}

  @media (max-width: 1000px) {{
    .doc-body {{ grid-template-columns: 1fr; min-height: auto; }}
    .pdf-viewer {{ border-right: none; border-bottom: 1px solid var(--border); max-height: 500px; }}
    .tab-content {{ min-height: 500px; }}
    .hero h1 {{ font-size: 1.8rem; }}
    .stats-bar {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>

<div class="hero">
  <h1><span class="accent">LiteParse</span> <span class="dim">vs</span> PyPDF <span class="dim">vs</span> PyMuPDF</h1>
  <p class="subtitle">
    Side-by-side table extraction on real government &amp; financial documents.
    See the original PDF on the left, then tab through each parser's output on the right.
  </p>
  <div class="badge-row">
    <span class="badge"><strong>Free</strong> &mdash; Apache 2.0</span>
    <span class="badge"><strong>No VLMs</strong> &mdash; Runs fully local</span>
    <span class="badge"><strong>Model-free</strong> &mdash; No API keys needed</span>
  </div>
  <div class="stats-bar">
    <div class="stat"><div class="val">{num_docs}</div><div class="lbl">Documents</div></div>
    <div class="stat"><div class="val">{total_pages}</div><div class="lbl">Pages Parsed</div></div>
    <div class="stat"><div class="val">{total_lp:.1f}s</div><div class="lbl">LiteParse Total</div></div>
    <div class="stat"><div class="val">3</div><div class="lbl">Parsers Compared</div></div>
  </div>
</div>

<div class="container">
  <nav class="doc-nav">
    {''.join(f'<a href="#doc-{i}">{esc(name.split("—")[0].strip())}</a>' for i, name in enumerate(results))}
  </nav>
  {''.join(doc_sections)}
</div>

<div class="footer">
  <div>Built with <a href="https://developers.llamaindex.ai/liteparse/">LiteParse</a> by <a href="https://www.llamaindex.ai">LlamaIndex</a></div>
  <div class="install">pip install liteparse</div>
</div>

<script>
document.querySelectorAll('.tab-btn').forEach(btn => {{
  btn.addEventListener('click', () => {{
    const card = btn.closest('.doc-card');
    card.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    card.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tab).classList.add('active');
  }});
}});
</script>

</body>
</html>
"""

output_path = OUTPUT_DIR / "comparison.html"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(html_content)
print(f"\nHTML comparison written to {output_path.resolve()}")
print(f"Total size: {output_path.stat().st_size / 1024:.1f} KB")
