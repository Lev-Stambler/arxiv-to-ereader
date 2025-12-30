"""Streamlit web interface for arxiv-epub."""

import tempfile
from pathlib import Path

import streamlit as st

from arxiv_epub.converter import convert_to_epub
from arxiv_epub.fetcher import (
    ArxivFetchError,
    ArxivHTMLNotAvailable,
    fetch_paper,
    normalize_arxiv_id,
)
from arxiv_epub.parser import parse_paper

st.set_page_config(
    page_title="arXiv to EPUB",
    page_icon="📚",
    layout="centered",
)

st.title("📚 arXiv to EPUB Converter")
st.markdown(
    "Convert arXiv papers to EPUB format for easy reading on your Kindle or e-reader."
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

col1, col2 = st.columns(2)

with col1:
    style_preset = st.selectbox(
        "Style preset",
        ["default", "compact", "large-text"],
        help="Choose a style preset for the EPUB",
    )

with col2:
    download_images = st.checkbox(
        "Include images",
        value=True,
        help="Download and embed images (unchecked = faster, smaller files)",
    )

# Convert button
if st.button("Convert to EPUB", type="primary", disabled=not paper_inputs):
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

            # Convert to EPUB
            status_text.text(f"Converting {paper_id} to EPUB...")

            with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
                output_path = Path(tmp.name)

            epub_path = convert_to_epub(
                paper,
                output_path=output_path,
                style_preset=style_preset,
                download_images=download_images,
            )

            results.append(
                {
                    "success": True,
                    "paper_id": paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "path": epub_path,
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

            # Read file and provide download
            with open(result["path"], "rb") as f:
                epub_data = f.read()

            st.download_button(
                label=f"📥 Download {result['paper_id']}.epub",
                data=epub_data,
                file_name=f"{result['paper_id'].replace('/', '_')}.epub",
                mime="application/epub+zip",
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
            <a href="https://github.com/Lev-Stambler/arxiv-epub" target="_blank">GitHub</a> •
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
