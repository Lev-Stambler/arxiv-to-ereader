"""Streamlit web interface for arxiv-to-ereader."""

import shutil
import tempfile
from pathlib import Path

import streamlit as st

from arxiv_to_ereader.converter import OutputFormat, convert_to_epub, validate_epub
from arxiv_to_ereader.fetcher import (
    ArxivFetchError,
    ArxivHTMLNotAvailable,
    fetch_paper,
    normalize_arxiv_id,
)
from arxiv_to_ereader.parser import parse_paper

st.set_page_config(
    page_title="arXiv to E-Reader",
    page_icon="📚",
    layout="centered",
)

st.title("📚 arXiv to E-Reader Converter")
st.markdown(
    "Convert arXiv papers to EPUB or Kindle formats for easy reading on your e-reader."
)

# Input section
st.subheader("Paper Input")

input_method = st.radio(
    "Input method:",
    ["Single paper", "Multiple papers"],
    horizontal=True,
)

if input_method == "Single paper":
    paper_input = st.text_input(
        "arXiv ID or URL",
        placeholder="e.g., 2402.08954 or https://arxiv.org/abs/2402.08954",
        help="Enter an arXiv paper ID or URL",
    )
    paper_inputs = [paper_input] if paper_input else []
else:
    paper_input = st.text_area(
        "arXiv IDs or URLs (one per line)",
        placeholder="2402.08954\n2401.12345\nhttps://arxiv.org/abs/2312.00001",
        help="Enter multiple arXiv paper IDs or URLs, one per line",
    )
    paper_inputs = [p.strip() for p in paper_input.strip().split("\n") if p.strip()]

# Options
st.subheader("Options")

col1, col2, col3 = st.columns(3)

with col1:
    output_format = st.selectbox(
        "Output format",
        ["EPUB", "AZW3 (Kindle)", "MOBI"],
        help="Choose the output format. AZW3 is recommended for Kindle devices.",
    )

with col2:
    style_preset = st.selectbox(
        "Style preset",
        ["default", "compact", "large-text"],
        help="Choose a style preset for the ebook",
    )

with col3:
    download_images = st.checkbox(
        "Include images",
        value=True,
        help="Download and embed images (unchecked = faster, smaller files)",
    )

# Map display names to OutputFormat enum
format_map = {
    "EPUB": OutputFormat.EPUB,
    "AZW3 (Kindle)": OutputFormat.AZW3,
    "MOBI": OutputFormat.MOBI,
}
selected_format = format_map[output_format]

# Check if Calibre is available for Kindle formats
calibre_available = shutil.which("ebook-convert") is not None
if selected_format in (OutputFormat.AZW3, OutputFormat.MOBI) and not calibre_available:
    st.warning(
        "⚠️ Calibre is required for AZW3/MOBI conversion but was not found. "
        "Please install Calibre or select EPUB format."
    )

# Get file extension and mime type
format_extensions = {
    OutputFormat.EPUB: (".epub", "application/epub+zip"),
    OutputFormat.AZW3: (".azw3", "application/octet-stream"),
    OutputFormat.MOBI: (".mobi", "application/x-mobipocket-ebook"),
}
file_ext, mime_type = format_extensions[selected_format]

# Convert button
button_label = f"Convert to {output_format.split()[0]}"
convert_disabled = not paper_inputs or (
    selected_format in (OutputFormat.AZW3, OutputFormat.MOBI) and not calibre_available
)

if st.button(button_label, type="primary", disabled=convert_disabled):
    results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, paper_input in enumerate(paper_inputs):
        progress = (i + 1) / len(paper_inputs)
        progress_bar.progress(progress)

        try:
            # Normalize ID
            status_text.text(f"Processing {paper_input}...")
            paper_id = normalize_arxiv_id(paper_input)

            # Fetch HTML
            status_text.text(f"Fetching {paper_id}...")
            _, html = fetch_paper(paper_id)

            # Parse HTML
            status_text.text(f"Parsing {paper_id}...")
            paper = parse_paper(html, paper_id)

            # Convert to selected format
            format_name = selected_format.value.upper()
            status_text.text(f"Converting {paper_id} to {format_name}...")

            with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
                output_path = Path(tmp.name)

            ebook_path = convert_to_epub(
                paper,
                output_path=output_path,
                style_preset=style_preset,
                download_images=download_images,
                output_format=selected_format,
            )

            # Validate EPUB if applicable
            validation_errors = []
            if selected_format == OutputFormat.EPUB:
                is_valid, validation_errors = validate_epub(ebook_path)
            else:
                is_valid = True

            results.append(
                {
                    "success": True,
                    "paper_id": paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "path": ebook_path,
                    "validation_passed": is_valid,
                    "validation_errors": validation_errors,
                }
            )

        except (ArxivHTMLNotAvailable, ArxivFetchError, ValueError) as e:
            results.append(
                {
                    "success": False,
                    "paper_id": paper_input,
                    "error": str(e),
                }
            )

        except Exception as e:
            results.append(
                {
                    "success": False,
                    "paper_id": paper_input,
                    "error": f"Unexpected error: {e}",
                }
            )

    progress_bar.empty()
    status_text.empty()

    # Show results
    st.subheader("Results")

    for result in results:
        if result["success"]:
            st.success(f"✅ {result['paper_id']}: {result['title']}")

            # Show validation warning if applicable
            if not result.get("validation_passed", True):
                st.warning(
                    "⚠️ **EPUB Validation Failed** - This file may be rejected by Send to Kindle. "
                    f"({len(result.get('validation_errors', []))} errors detected)"
                )
                with st.expander("Show validation errors"):
                    for error in result.get("validation_errors", [])[:10]:
                        st.code(error)
                    if len(result.get("validation_errors", [])) > 10:
                        st.write(f"... and {len(result['validation_errors']) - 10} more errors")

            # Read file and provide download
            with open(result["path"], "rb") as f:
                ebook_data = f.read()

            st.download_button(
                label=f"📥 Download {result['paper_id']}{file_ext}",
                data=ebook_data,
                file_name=f"{result['paper_id'].replace('/', '_')}{file_ext}",
                mime=mime_type,
            )

            with st.expander("Paper details"):
                st.write(f"**Authors:** {', '.join(result['authors'])}")

        else:
            st.error(f"❌ {result['paper_id']}: {result['error']}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        <p>
            <a href="https://github.com/Lev-Stambler/arxiv-to-ereader" target="_blank">GitHub</a> •
            <a href="https://arxiv.org" target="_blank">arXiv</a>
        </p>
        <p>Made with ❤️ for researchers</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """Entry point for the Streamlit app (called via streamlit run)."""
    pass  # Streamlit runs the module directly


if __name__ == "__main__":
    main()
