# arxiv-epub

Convert arXiv HTML papers to EPUB format for easy reading on Kindle and other e-readers.

## Features

- **Simple CLI**: Convert papers with a single command
- **Batch Processing**: Convert multiple papers at once
- **Responsive Design**: Optimized CSS for all Kindle devices (Paperwhite, Oasis, Fire)
- **Web Interface**: Optional Streamlit UI for non-technical users
- **Flexible Input**: Accepts arXiv IDs or URLs
- **Multiple Styles**: Choose from default, compact, or large-text presets

## Installation

### Using uv (recommended)

```bash
uv pip install arxiv-epub
```

### From source

```bash
git clone https://github.com/Lev-Stambler/arxiv-epub.git
cd arxiv-epub
uv sync
```

## Usage

### Command Line

```bash
# Convert a single paper
arxiv-epub 2402.08954

# Convert from URL
arxiv-epub https://arxiv.org/abs/2402.08954

# Convert multiple papers
arxiv-epub 2402.08954 2401.12345 2312.00001

# Specify output directory
arxiv-epub 2402.08954 -o ~/kindle-papers/

# Use a different style preset
arxiv-epub 2402.08954 --style large-text

# Skip images for faster/smaller files
arxiv-epub 2402.08954 --no-images
```

### Style Presets

- `default`: Balanced readability for most devices
- `compact`: Smaller text, more content per page
- `large-text`: Larger text for easier reading

### Web Interface (Streamlit)

Run the web interface locally:

```bash
uv pip install arxiv-epub[web]
streamlit run src/arxiv_epub/web.py
```

## Python API

```python
from arxiv_epub import fetch_paper, parse_paper, convert_to_epub

# Fetch and convert a paper
paper_id, html = fetch_paper("2402.08954")
paper = parse_paper(html, paper_id)
epub_path = convert_to_epub(paper, output_path="paper.epub")

print(f"Created: {epub_path}")
print(f"Title: {paper.title}")
print(f"Authors: {', '.join(paper.authors)}")
```

## Requirements

- Python 3.10+
- arXiv papers with HTML version available (papers submitted after Dec 2023)

## Limitations

- Only works with arXiv papers that have HTML versions
- Papers submitted before December 2023 may not have HTML available
- Complex mathematical equations may not render perfectly on all e-readers

## Development

```bash
# Clone the repo
git clone https://github.com/Lev-Stambler/arxiv-epub.git
cd arxiv-epub

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
3. **Convert**: Creates an EPUB file using ebooklib with responsive CSS styling

The generated EPUB includes:
- Cover page with title, authors, and paper ID
- Abstract
- All paper sections
- Embedded figures (optional)
- References
- Responsive CSS optimized for Kindle devices

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [arXiv](https://arxiv.org) for providing HTML versions of papers
- [ebooklib](https://github.com/aerkalov/ebooklib) for EPUB generation
- [LaTeXML](https://dlmf.nist.gov/LaTeXML/) which powers arXiv's HTML conversion

## Disclaimer

This software is provided "as is", without warranty of any kind. The authors are not liable for any damages or issues arising from the use of this software. This tool is for personal use and research purposes. Please respect arXiv's terms of service and rate limits.
