"""
LiteParse Visual Citations — Interactive Demo Generator

Parses PDFs with LiteParse (JSON mode for bounding boxes), takes screenshots,
and generates a self-contained HTML page where users can search text and see
highlights drawn on the source page images.

Configuration: edit docs.json to add/remove documents and pages.
"""

import base64
import html
import json
import time
from pathlib import Path

from liteparse import LiteParse

# ── Config ──────────────────────────────────────────────────────────────
DPI = 150
SCALE = DPI / 72  # PDF points → pixels
DATA_DIR = Path("../data")
OUTPUT_DIR = Path("output")

with open("docs.json") as f:
    DOCS_CONFIG = json.load(f)


def esc(s: str) -> str:
    return html.escape(s)


# ── Parse & screenshot ──────────────────────────────────────────────────
parser = LiteParse()
all_docs = []

for cfg in DOCS_CONFIG:
    name = cfg["name"]
    filepath = str(DATA_DIR / cfg["file"])
    page_str = ",".join(str(p + 1) for p in cfg["pages"])
    print(f"Parsing: {name} (pages {page_str})")

    t0 = time.perf_counter()
    result = parser.parse(filepath, target_pages=page_str, dpi=DPI)
    elapsed = time.perf_counter() - t0

    screenshots = parser.screenshot(
        filepath, target_pages=page_str, dpi=DPI, load_bytes=True
    )

    # Build page data
    pages_data = []
    for page in result.pages:
        # Find matching screenshot
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

        pages_data.append({
            "pageNum": page.pageNum,
            "width": page.width,
            "height": page.height,
            "text": page.text,
            "textItems": text_items,
            "image": img_b64,
        })

    all_docs.append({
        "name": name,
        "source": cfg["source"],
        "parseTime": round(elapsed, 3),
        "pages": pages_data,
    })
    print(f"  Done in {elapsed:.2f}s — {len(pages_data)} pages, "
          f"{sum(len(p['textItems']) for p in pages_data)} text items")


# ── Generate HTML ───────────────────────────────────────────────────────
# Strip image data from JSON (we'll embed images separately to keep JSON smaller)
docs_json_items = []
for doc in all_docs:
    slim_pages = []
    for page in doc["pages"]:
        slim_pages.append({
            "pageNum": page["pageNum"],
            "width": page["width"],
            "height": page["height"],
            "text": page["text"],
            "textItems": page["textItems"],
        })
    docs_json_items.append({
        "name": doc["name"],
        "source": doc["source"],
        "parseTime": doc["parseTime"],
        "pages": slim_pages,
    })

docs_json = json.dumps(docs_json_items)

# Build image map: docIdx -> pageIdx -> base64
image_tags = []
for di, doc in enumerate(all_docs):
    for pi, page in enumerate(doc["pages"]):
        if page["image"]:
            image_tags.append(
                f'<img id="img-{di}-{pi}" class="hidden-img" '
                f'src="data:image/png;base64,{page["image"]}" />'
            )

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LiteParse Visual Citations — Interactive Demo</title>
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
    --yellow: #FEEE05;
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
    padding: 2.5rem 2rem 2rem;
    background: linear-gradient(180deg, rgba(62,24,249,0.04) 0%, transparent 70%);
    border-bottom: 1px solid var(--border);
  }}
  .hero h1 {{ font-size: 2.2rem; font-weight: 500; letter-spacing: -0.03em; line-height: 1.1; margin-bottom: 0.4rem; }}
  .hero h1 .accent {{ color: var(--purple); }}
  .hero .subtitle {{ color: var(--text-dim); font-size: 1rem; max-width: 620px; margin: 0 auto; }}

  /* Controls bar */
  .controls {{
    display: flex; gap: 0.8rem; align-items: center; flex-wrap: wrap;
    padding: 1rem 1.5rem;
    background: var(--bg-alt); border-bottom: 1px solid var(--border);
    max-width: 1500px; margin: 0 auto;
  }}
  .controls label {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; color: var(--text-dim); font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.04em;
  }}
  .controls select, .controls input[type="text"] {{
    background: var(--bg); color: var(--text); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.5rem 0.8rem; font-size: 0.88rem; font-family: inherit;
    outline: none; transition: border-color 0.15s;
  }}
  .controls select:focus, .controls input:focus {{ border-color: var(--purple); }}
  .controls select {{ min-width: 320px; }}
  .controls input[type="text"] {{ flex: 1; min-width: 200px; }}
  .search-btn {{
    background: var(--gradient-brand); color: #fff; border: none; border-radius: 20px;
    padding: 0.5rem 1.5rem; font-size: 0.75rem; font-weight: 500; cursor: pointer;
    font-family: 'IBM Plex Mono', monospace; text-transform: uppercase; letter-spacing: 0.04em;
    transition: opacity 0.15s;
  }}
  .search-btn:hover {{ opacity: 0.85; }}
  .match-count {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.82rem; color: var(--text-dim); min-width: 100px;
    font-variant-numeric: tabular-nums;
  }}

  /* Main layout */
  .main {{
    display: grid; grid-template-columns: minmax(600px, 1fr) minmax(0, 1fr);
    max-width: 1500px; margin: 0 auto;
    min-height: calc(100vh - 180px);
  }}

  /* Left: page viewer */
  .viewer {{
    border-right: 1px solid var(--border);
    display: flex; flex-direction: column;
    background: var(--bg-alt);
  }}
  .viewer-header {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 0.5rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; font-weight: 500; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
  }}
  .page-nav {{ display: flex; gap: 0.3rem; }}
  .page-btn {{
    background: var(--bg-alt); color: var(--text-dim); border: 1px solid var(--border);
    border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.78rem; cursor: pointer;
    font-family: inherit; transition: all 0.15s;
  }}
  .page-btn:hover {{ background: var(--surface3); color: var(--text); }}
  .page-btn.active {{ background: var(--purple); color: #fff; border-color: var(--purple); font-weight: 500; }}
  .canvas-wrap {{
    flex: 1; overflow: auto; position: relative;
    display: flex; align-items: flex-start; justify-content: center;
    padding: 1rem;
  }}
  .canvas-container {{
    position: relative;
    display: inline-block;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    border-radius: 4px;
    overflow: hidden;
  }}
  .canvas-container img {{
    display: block;
    max-width: 100%;
    height: auto;
  }}
  .canvas-container canvas {{
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
  }}

  /* Right: text viewer */
  .text-panel {{
    display: flex; flex-direction: column;
    min-width: 0; overflow: hidden;
  }}
  .text-header {{
    padding: 0.5rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; font-weight: 500; color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.04em;
    border-bottom: 1px solid var(--border);
    background: var(--bg);
    display: flex; justify-content: space-between; align-items: center;
  }}
  .parse-time {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; color: var(--purple);
  }}
  .text-content {{
    flex: 1; overflow: auto;
    padding: 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem; line-height: 1.55;
    white-space: pre;
    background: var(--bg-alt);
    tab-size: 4;
  }}
  .text-content mark {{
    background: rgba(254, 238, 5, 0.35);
    color: var(--text);
    border-radius: 2px;
    padding: 0 1px;
  }}

  .hidden-img {{ display: none !important; }}

  /* Footer */
  .footer {{
    text-align: center; padding: 2rem;
    color: var(--text-dim); font-size: 0.82rem; border-top: 1px solid var(--border);
    max-width: 1500px; margin: 0 auto;
  }}
  .footer a {{ color: var(--purple); text-decoration: none; }}
  .footer a:hover {{ text-decoration: underline; }}
  .footer .install {{
    display: inline-block; background: var(--bg-alt); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.4rem 1rem;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.9rem; margin-top: 0.6rem; color: var(--purple);
  }}

  @media (max-width: 1000px) {{
    .main {{ grid-template-columns: 1fr; }}
    .viewer {{ border-right: none; border-bottom: 1px solid var(--border); max-height: 60vh; }}
  }}
</style>
</head>
<body>

<div class="hero">
  <h1><span class="accent">LiteParse</span> Visual Citations</h1>
  <p class="subtitle">Exact keyword search over parsed text &mdash; see precisely where each match appears on the source PDF page, highlighted with bounding boxes from LiteParse.</p>
</div>

<div class="controls">
  <label for="doc-select">Document</label>
  <select id="doc-select"></select>
  <label for="search-input">Search</label>
  <input type="text" id="search-input" placeholder="Exact keyword search (e.g. &quot;Total&quot;, &quot;assets&quot;)..." />
  <button class="search-btn" id="search-btn">Search</button>
  <span class="match-count" id="match-count"></span>
</div>

<div class="main">
  <div class="viewer">
    <div class="viewer-header">
      <span>Source PDF Page</span>
      <div class="page-nav" id="page-nav"></div>
    </div>
    <div class="canvas-wrap">
      <div class="canvas-container" id="canvas-container">
        <img id="page-img" src="" alt="PDF page" />
        <canvas id="highlight-canvas"></canvas>
      </div>
    </div>
  </div>
  <div class="text-panel">
    <div class="text-header">
      <span>Parsed Text (LiteParse)</span>
      <span class="parse-time" id="parse-time"></span>
    </div>
    <div class="text-content" id="text-content"></div>
  </div>
</div>

<div class="footer">
  <div>Built with <a href="https://developers.llamaindex.ai/liteparse/">LiteParse</a> by <a href="https://www.llamaindex.ai">LlamaIndex</a></div>
  <div class="install">pip install liteparse</div>
</div>

<!-- Hidden images for each page -->
{''.join(image_tags)}

<script>
const DOCS = {docs_json};
const SCALE = {SCALE};

let currentDoc = 0;
let currentPage = 0;
let currentQuery = "";

const docSelect = document.getElementById("doc-select");
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const matchCount = document.getElementById("match-count");
const pageNav = document.getElementById("page-nav");
const pageImg = document.getElementById("page-img");
const canvas = document.getElementById("highlight-canvas");
const ctx = canvas.getContext("2d");
const textContent = document.getElementById("text-content");
const parseTime = document.getElementById("parse-time");

// Populate doc selector
DOCS.forEach((doc, i) => {{
  const opt = document.createElement("option");
  opt.value = i;
  opt.textContent = doc.name + " (" + doc.source + ")";
  docSelect.appendChild(opt);
}});

function loadDoc(docIdx) {{
  currentDoc = docIdx;
  currentPage = 0;
  const doc = DOCS[docIdx];
  parseTime.textContent = doc.parseTime + "s";

  // Build page nav buttons
  pageNav.innerHTML = "";
  doc.pages.forEach((page, pi) => {{
    const btn = document.createElement("button");
    btn.className = "page-btn" + (pi === 0 ? " active" : "");
    btn.textContent = "Page " + page.pageNum;
    btn.addEventListener("click", () => loadPage(pi));
    pageNav.appendChild(btn);
  }});

  loadPage(0);
}}

function loadPage(pageIdx) {{
  currentPage = pageIdx;
  const doc = DOCS[currentDoc];
  const page = doc.pages[pageIdx];

  // Update nav active state
  pageNav.querySelectorAll(".page-btn").forEach((btn, i) => {{
    btn.classList.toggle("active", i === pageIdx);
  }});

  // Load image from hidden img
  const hiddenImg = document.getElementById("img-" + currentDoc + "-" + pageIdx);
  if (hiddenImg) {{
    pageImg.src = hiddenImg.src;
    pageImg.onload = () => {{
      canvas.width = pageImg.naturalWidth;
      canvas.height = pageImg.naturalHeight;
      drawHighlights();
    }};
  }}

  // Render text with highlights
  renderText();
}}

function searchTextItems(textItems, query) {{
  if (!query || !textItems.length) return [];
  const q = query.toLowerCase();

  // Build a single concatenated string and track which character
  // ranges belong to which textItem.
  let fullText = "";
  const ranges = []; // {{ charStart, charEnd, item }}
  for (const item of textItems) {{
    const trimmed = item.text.replace(/\s+$/, "");
    if (!trimmed) continue;
    if (fullText.length > 0) fullText += " ";
    const start = fullText.length;
    fullText += trimmed;
    ranges.push({{ charStart: start, charEnd: fullText.length, item }});
  }}

  // Find every occurrence of the query in the full text
  const lower = fullText.toLowerCase();
  const matches = [];
  let pos = 0;
  while ((pos = lower.indexOf(q, pos)) !== -1) {{
    const matchEnd = pos + q.length;

    // Collect only the textItems whose character range overlaps the match
    const overlapping = ranges.filter(
      r => r.charStart < matchEnd && r.charEnd > pos
    );

    if (overlapping.length) {{
      const xs  = overlapping.map(r => r.item.x);
      const ys  = overlapping.map(r => r.item.y);
      const x2s = overlapping.map(r => r.item.x + r.item.width);
      const y2s = overlapping.map(r => r.item.y + r.item.height);
      matches.push({{
        text: fullText.substring(pos, matchEnd),
        x: Math.min(...xs),
        y: Math.min(...ys),
        width:  Math.max(...x2s) - Math.min(...xs),
        height: Math.max(...y2s) - Math.min(...ys),
      }});
    }}
    pos += 1;
  }}

  return matches;
}}

function drawHighlights() {{
  const doc = DOCS[currentDoc];
  const page = doc.pages[currentPage];
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  if (!currentQuery) return;

  const matches = searchTextItems(page.textItems, currentQuery);

  // Scale: image pixel dimensions vs PDF points
  const imgW = pageImg.naturalWidth;
  const imgH = pageImg.naturalHeight;
  const scaleX = imgW / (page.width * SCALE);
  const scaleY = imgH / (page.height * SCALE);

  ctx.fillStyle = "rgba(254, 238, 5, 0.35)";
  ctx.strokeStyle = "rgba(254, 238, 5, 0.8)";
  ctx.lineWidth = 2;

  for (const m of matches) {{
    const x = m.x * SCALE * scaleX;
    const y = m.y * SCALE * scaleY;
    const w = m.width * SCALE * scaleX;
    const h = m.height * SCALE * scaleY;
    ctx.fillRect(x, y, w, h);
    ctx.strokeRect(x, y, w, h);
  }}

  // Update match count across all pages
  let totalMatches = 0;
  for (const p of doc.pages) {{
    totalMatches += searchTextItems(p.textItems, currentQuery).length;
  }}
  matchCount.textContent = totalMatches + " match" + (totalMatches !== 1 ? "es" : "");
}}

function renderText() {{
  const doc = DOCS[currentDoc];
  const page = doc.pages[currentPage];
  const raw = page.text;

  if (!currentQuery) {{
    textContent.innerHTML = escapeHtml(raw);
    return;
  }}

  // Highlight matches in text
  const escaped = escapeHtml(raw);
  const q = escapeHtml(currentQuery);
  const regex = new RegExp("(" + escapeRegex(q) + ")", "gi");
  textContent.innerHTML = escaped.replace(regex, "<mark>$1</mark>");
}}

function escapeHtml(s) {{
  const d = document.createElement("div");
  d.appendChild(document.createTextNode(s));
  return d.innerHTML;
}}

function escapeRegex(s) {{
  return s.replace(/[.*+?^${{}}()|[\\]\\\\]/g, "\\\\$&");
}}

function doSearch() {{
  currentQuery = searchInput.value.trim();
  if (!currentQuery) {{
    matchCount.textContent = "";
  }}
  drawHighlights();
  renderText();
}}

docSelect.addEventListener("change", (e) => loadDoc(+e.target.value));
searchBtn.addEventListener("click", doSearch);
searchInput.addEventListener("keydown", (e) => {{
  if (e.key === "Enter") doSearch();
}});

// Init
loadDoc(0);
</script>

</body>
</html>
"""

output_path = OUTPUT_DIR / "visual-citations.html"
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(html_content)
print(f"\nHTML written to {output_path.resolve()}")
print(f"Size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
