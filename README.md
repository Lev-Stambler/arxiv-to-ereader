# arxiv-to-ereader

Convert arXiv HTML papers to EPUB and Kindle formats (MOBI, AZW3) for easy reading on e-readers.

![Demo](demo.gif)

## Quick Start

```bash
# Install
git clone https://github.com/Lev-Stambler/arxiv-to-ereader.git
cd arxiv-to-ereader
uv sync

# Convert a paper to EPUB
uv run arxiv-to-ereader 2402.08954

# Convert to native Kindle format (requires Calibre)
uv run arxiv-to-ereader 2402.08954 --format azw3

# Or use the web interface
uv sync --extra web
uv run streamlit run src/arxiv_to_ereader/web.py
```

## Features

- **Multiple Formats**: Output to EPUB, MOBI, or AZW3 (native Kindle format)
- **Math Rendering**: LaTeX equations converted to images with proper baseline alignment for Kindle compatibility
- **Simple CLI**: Convert papers with a single command
- **Batch Processing**: Convert multiple papers at once
- **Web Interface**: Optional Streamlit UI for non-technical users
- **Responsive Design**: Optimized CSS for Kindle devices (Paperwhite, Oasis, Fire)
- **Flexible Input**: Accepts arXiv IDs or URLs
- **Multiple Styles**: Choose from default, compact, or large-text presets

## Installation

### From source

```bash
git clone https://github.com/Lev-Stambler/arxiv-to-ereader.git
cd arxiv-to-ereader
uv sync
```

### Kindle Format Support (Optional)

To convert to native Kindle formats (MOBI/AZW3), install [Calibre](https://calibre-ebook.com/download):

```bash
# macOS
brew install calibre

# Ubuntu/Debian
sudo apt install calibre
```

## Usage

### Command Line

```bash
# Convert a single paper to EPUB (default)
uv run arxiv-to-ereader 2402.08954

# Convert to native Kindle format (AZW3 - recommended for Kindle)
uv run arxiv-to-ereader 2402.08954 --format azw3

# Convert to MOBI format
uv run arxiv-to-ereader 2402.08954 --format mobi

# Convert from URL
uv run arxiv-to-ereader https://arxiv.org/abs/2402.08954

# Convert multiple papers
uv run arxiv-to-ereader 2402.08954 2401.12345 2312.00001 -f azw3

# Specify output directory
uv run arxiv-to-ereader 2402.08954 -o ~/kindle-papers/ -f azw3

# Use a different style preset
uv run arxiv-to-ereader 2402.08954 --style large-text

# Skip images for faster/smaller files
uv run arxiv-to-ereader 2402.08954 --no-images

# Keep MathML instead of rendering to images (not recommended for Kindle)
uv run arxiv-to-ereader 2402.08954 --no-math-images

# Increase math image resolution for larger screens
uv run arxiv-to-ereader 2402.08954 --math-dpi 200

# Use arXiv ID for filename instead of paper title
uv run arxiv-to-ereader 2402.08954 --use-id
```

### Output Formats

| Format | Extension | Description |
|--------|-----------|-------------|
| `epub` | `.epub` | Universal e-book format (default) |
| `azw3` | `.azw3` | Native Kindle format (KF8) - recommended for Kindle |
| `mobi` | `.mobi` | Legacy Kindle format |

**Note**: AZW3 is the recommended format for Kindle devices as it supports the latest Kindle features and typography.

### Style Presets

- `default`: Balanced readability for most devices
- `compact`: Smaller text, more content per page
- `large-text`: Larger text for easier reading

### Web Interface

![Web Interface](demo-web.gif)

Run the web interface locally:

```bash
uv sync --extra web
uv run streamlit run src/arxiv_to_ereader/web.py
```

The web interface supports:
- Single or batch paper conversion
- Format selection (EPUB, MOBI, AZW3)
- Style presets
- Image inclusion toggle

## Python API

```python
from arxiv_to_ereader import fetch_paper, parse_paper, convert_to_epub, OutputFormat

# Fetch and convert a paper to EPUB
paper_id, html = fetch_paper("2402.08954")
paper = parse_paper(html, paper_id)
epub_path = convert_to_epub(paper, output_path="paper.epub")

# Convert to native Kindle format (AZW3) with math as images
azw3_path = convert_to_epub(
    paper,
    output_path="paper.azw3",
    output_format=OutputFormat.AZW3,
    render_math=True,  # Convert LaTeX to images (default)
    math_dpi=150,      # Image resolution
)

# Keep MathML (for EPUB readers that support it)
epub_path = convert_to_epub(
    paper,
    output_path="paper.epub",
    render_math=False,
)

print(f"Created: {azw3_path}")
print(f"Title: {paper.title}")
print(f"Authors: {', '.join(paper.authors)}")
```

## Requirements

- Python 3.10+
- arXiv papers with HTML version available (papers submitted after Dec 2023)
- [Calibre](https://calibre-ebook.com/download) (optional, for MOBI/AZW3 conversion)

## Limitations

- Only works with arXiv papers that have HTML versions
- Papers submitted before December 2023 may not have HTML available
- Very complex LaTeX equations may fall back to simplified rendering
- MOBI/AZW3 conversion requires Calibre to be installed

## Development

```bash
# Clone the repo
git clone https://github.com/Lev-Stambler/arxiv-to-ereader.git
cd arxiv-to-ereader

# Install with dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Run linting
uv run ruff check src tests
```

## How It Works

1. **Fetch**: Downloads the HTML version of the paper from arXiv
2. **Parse**: Extracts title, authors, abstract, sections, figures, and references
3. **Render Math**: Converts LaTeX equations to PNG images using matplotlib with proper baseline alignment for inline math
4. **Convert**: Creates an EPUB file using ebooklib with responsive CSS styling
5. **Transform** (optional): Converts EPUB to Kindle formats using Calibre

The generated ebook includes:
- Cover page with title, authors, and paper ID
- Abstract
- All paper sections with math equations rendered as images
- Embedded figures (optional)
- Footnotes
- References
- Responsive CSS optimized for e-reader devices

Output files are named after the paper title by default (use `--use-id` for arXiv ID-based filenames).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [arXiv](https://arxiv.org) for providing HTML versions of papers
- [ebooklib](https://github.com/aerkalov/ebooklib) for EPUB generation
- [matplotlib](https://matplotlib.org) for LaTeX equation rendering
- [Calibre](https://calibre-ebook.com) for Kindle format conversion
- [LaTeXML](https://dlmf.nist.gov/LaTeXML/) which powers arXiv's HTML conversion

## Recording the Demos

The CLI demo is recorded using [VHS](https://github.com/charmbracelet/vhs):

```bash
# Install VHS (https://github.com/charmbracelet/vhs#installation)
vhs demo-quick.tape    # Quick CLI demo (no network)
vhs demo.tape          # Full CLI demo (requires network)
```

The web demo is recorded using Playwright:

```bash
uv run python scripts/record_web_demo.py
```

## Disclaimer

This software is provided "as is", without warranty of any kind. The authors are not liable for any damages or issues arising from the use of this software. This tool is for personal use and research purposes. Please respect arXiv's terms of service and rate limits.
