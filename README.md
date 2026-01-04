# arxiv-ereader

Convert arXiv HTML papers to PDF optimized for e-readers (Kindle, Kobo, reMarkable).

## Quick Start

```bash
# Install
git clone https://github.com/Lev-Stambler/arxiv-to-ereader.git
cd arxiv-to-ereader
uv sync

# Install Playwright browser
uv run playwright install chromium

# Convert a paper to PDF (default: Kindle Paperwhite)
uv run arxiv-ereader 2402.08954

# Convert for Kindle Scribe
uv run arxiv-ereader 2402.08954 --screen kindle-scribe

# Or use the web interface
uv sync --extra web
uv run streamlit run src/arxiv_to_ereader/web.py
```

## Features

- **Screen Presets**: Optimized page sizes for popular e-readers (Kindle, Kobo, reMarkable)
- **Native Math Rendering**: MathML equations rendered by browser engine (same as viewing on arXiv)
- **Table Support**: Handles LaTeXML's span-based tables with proper CSS styling
- **Algorithm Blocks**: Converts algorithm pseudocode from SVG to readable HTML blocks
- **Simple CLI**: Convert papers with a single command
- **Batch Processing**: Convert multiple papers at once
- **Web Interface**: Optional Streamlit UI
- **Custom Dimensions**: Specify exact page dimensions in mm

## Installation

```bash
git clone https://github.com/Lev-Stambler/arxiv-to-ereader.git
cd arxiv-to-ereader
uv sync

# Install Playwright's Chromium browser
uv run playwright install chromium
```

## Usage

### Command Line

```bash
# Convert a single paper (default preset: kindle-paperwhite)
uv run arxiv-ereader 2402.08954

# List available screen presets
uv run arxiv-ereader --list-screens

# Use a specific preset
uv run arxiv-ereader 2402.08954 --screen kindle-scribe
uv run arxiv-ereader 2402.08954 --screen remarkable
uv run arxiv-ereader 2402.08954 --screen kobo-libra

# Custom page dimensions (in mm)
uv run arxiv-ereader 2402.08954 --width 150 --height 200

# Convert from URL
uv run arxiv-ereader https://arxiv.org/abs/2402.08954

# Convert multiple papers
uv run arxiv-ereader 2402.08954 2401.12345 2312.00001

# Specify output directory
uv run arxiv-ereader 2402.08954 -o ~/papers/

# Skip images for faster/smaller files
uv run arxiv-ereader 2402.08954 --no-images

# Use arXiv ID for filename instead of paper title
uv run arxiv-ereader 2402.08954 --use-id
```

### Screen Presets

| Preset | Device | Dimensions |
|--------|--------|------------|
| `kindle-paperwhite` | Kindle Paperwhite 6.8" (2021+) | 105x140mm |
| `kindle-paperwhite-6` | Kindle Paperwhite 6" (older) | 91x123mm |
| `kindle-scribe` | Kindle Scribe 10.2" | 158x210mm |
| `kobo-clara` | Kobo Clara 6" | 91x123mm |
| `kobo-libra` | Kobo Libra 7" | 107x142mm |
| `remarkable` | reMarkable 2 10.3" | 158x210mm |
| `a5` | A5 paper size | 148x210mm |

### Web Interface

```bash
uv sync --extra web
uv run streamlit run src/arxiv_to_ereader/web.py
```

## Python API

```python
from arxiv_to_ereader import fetch_paper, parse_paper, convert_to_pdf, SCREEN_PRESETS

# Fetch and convert a paper
paper_id, html = fetch_paper("2402.08954")
paper = parse_paper(html, paper_id)

# Convert with default preset (kindle-paperwhite)
pdf_path = convert_to_pdf(paper, output_path="paper.pdf")

# Convert for Kindle Scribe
pdf_path = convert_to_pdf(
    paper,
    output_path="paper.pdf",
    screen_preset="kindle-scribe",
)

# Custom dimensions
pdf_path = convert_to_pdf(
    paper,
    output_path="paper.pdf",
    custom_width_mm=150,
    custom_height_mm=200,
)

print(f"Created: {pdf_path}")
print(f"Title: {paper.title}")
```

## Requirements

- Python 3.10+
- arXiv papers with HTML version available (papers submitted after Dec 2023)

## Development

```bash
# Clone the repo
git clone https://github.com/Lev-Stambler/arxiv-to-ereader.git
cd arxiv-to-ereader

# Install with dev dependencies
uv sync --all-extras

# Install Playwright browser
uv run playwright install chromium

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
```

## How It Works

1. **Fetch**: Downloads the HTML version of the paper from arXiv
2. **Parse**: Extracts title, authors, abstract, sections, figures, and references
   - Converts LaTeXML span-based tables (`ltx_tabular`) to properly styled tables
   - Extracts algorithm pseudocode from SVG foreignobjects and renders as HTML blocks
3. **Generate PDF**: Uses Playwright (headless Chromium) to render HTML with native MathML support and export to PDF with custom page dimensions

## Limitations

- Only works with arXiv papers that have HTML versions
- Papers submitted before December 2023 may not have HTML available

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [arXiv](https://arxiv.org) for providing HTML versions of papers
- [Playwright](https://playwright.dev/) for browser-based PDF generation
- [LaTeXML](https://dlmf.nist.gov/LaTeXML/) which powers arXiv's HTML conversion
