"""Parse arXiv HTML papers."""

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag


@dataclass
class Figure:
    """A figure from the paper."""

    id: str
    caption: str
    image_url: str | None = None
    image_data: bytes | None = None
    image_type: str = "image/png"


@dataclass
class Section:
    """A section of the paper."""

    id: str
    title: str
    level: int  # 1 = h1, 2 = h2, etc.
    content: str  # HTML content


@dataclass
class Footnote:
    """A footnote from the paper."""

    id: str
    index: int
    content: str  # HTML content


@dataclass
class Paper:
    """Parsed arXiv paper."""

    id: str
    title: str
    authors: list[str]
    abstract: str
    date: str | None = None
    sections: list[Section] = field(default_factory=list)
    figures: list[Figure] = field(default_factory=list)
    footnotes: list[Footnote] = field(default_factory=list)
    references_html: str | None = None
    base_url: str | None = None
    # Map of original image src -> absolute URL for ALL images in the paper
    all_images: dict[str, str] = field(default_factory=dict)


def _clean_text(text: str) -> str:
    """Clean up text by normalizing whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def _process_content(soup_fragment: Tag, footnote_counter: list[int]) -> tuple[str, list[Footnote]]:
    """Process HTML content for better EPUB compatibility.

    Handles:
    - Wrapping tables for responsive scrolling
    - Extracting and linking footnotes
    - Adding classes to code blocks
    - Cleaning up math structures
    - Styling theorems/proofs/definitions

    Args:
        soup_fragment: The BeautifulSoup Tag containing the content
        footnote_counter: Mutable list with single int for global footnote counting

    Returns:
        Tuple of (processed_html_string, list_of_footnotes)
    """
    footnotes: list[Footnote] = []

    # Helper to create new tags
    def new_tag(name: str, attrs: dict | None = None) -> Tag:
        tag = BeautifulSoup(f"<{name}></{name}>", "lxml").find(name)
        if attrs:
            for k, v in attrs.items():
                tag[k] = v
        return tag

    # 0. Clean up image alt text - remove useless "Refer to caption" placeholder
    for img in soup_fragment.find_all("img"):
        alt = img.get("alt", "")
        if alt.lower() in ["refer to caption", "refer to caption."]:
            # Try to find a better alt text from nearby caption
            figure = img.find_parent("figure")
            if figure:
                caption = figure.select_one(".ltx_caption, figcaption")
                if caption:
                    # Use first part of caption as alt text
                    caption_text = _clean_text(caption.get_text())
                    img["alt"] = caption_text[:100] if len(caption_text) > 100 else caption_text
                else:
                    img["alt"] = "Figure"
            else:
                img["alt"] = "Image"

    # 1. Handle Tables: Wrap in div for horizontal scrolling on e-readers
    for table in soup_fragment.select(".ltx_tabular, .ltx_table, table"):
        if table.parent and "table-wrapper" not in table.parent.get("class", []):
            wrapper = new_tag("div", {"class": "table-wrapper"})
            table.wrap(wrapper)

    # 2. Handle Footnotes: Extract inline notes and replace with links
    # LaTeXML uses class="ltx_note" for footnotes
    for note in soup_fragment.select(".ltx_note"):
        footnote_counter[0] += 1
        idx = footnote_counter[0]
        note_id = f"fn-{idx}"
        back_id = f"fnref-{idx}"

        # Get the note content (skip the note mark if present)
        note_content_elem = note.select_one(".ltx_note_content")
        if note_content_elem:
            note_content = "".join(str(c) for c in note_content_elem.children)
        else:
            note_content = "".join(str(c) for c in note.children)

        footnotes.append(Footnote(id=note_id, index=idx, content=note_content.strip()))

        # Replace note with a superscript link
        link = new_tag("a", {
            "href": f"#{note_id}",
            "id": back_id,
            "class": "footnote-ref",
            "epub:type": "noteref",
            "role": "doc-noteref",
        })
        sup = new_tag("sup")
        sup.string = str(idx)
        link.append(sup)
        note.replace_with(link)

    # 3. Handle Code Blocks: Ensure proper styling
    for listing in soup_fragment.select(".ltx_listing, .ltx_verbatim"):
        existing_classes = listing.get("class", [])
        if "code-block" not in existing_classes:
            listing["class"] = existing_classes + ["code-block"]

    # 4. Handle Theorems, Proofs, Definitions, Lemmas
    # LaTeXML uses ltx_theorem, ltx_proof, etc.
    theorem_classes = [
        "ltx_theorem",
        "ltx_proof",
        "ltx_lemma",
        "ltx_definition",
        "ltx_corollary",
        "ltx_proposition",
        "ltx_remark",
        "ltx_example",
    ]
    for cls in theorem_classes:
        for elem in soup_fragment.select(f".{cls}"):
            # Add epub-friendly class
            existing = elem.get("class", [])
            if "theorem-like" not in existing:
                elem["class"] = existing + ["theorem-like"]

    # 5. Handle equations - ensure they have proper wrappers
    for eq in soup_fragment.select(".ltx_equation, .ltx_equationgroup"):
        existing = eq.get("class", [])
        if "math-block" not in existing:
            eq["class"] = existing + ["math-block"]

    # 6. Handle inline math - add class for styling
    for math in soup_fragment.select(".ltx_Math"):
        existing = math.get("class", [])
        if "math-inline" not in existing:
            math["class"] = existing + ["math-inline"]

    # 7. Handle cross-references - ensure they work in EPUB
    for ref in soup_fragment.select(".ltx_ref"):
        href = ref.get("href", "")
        # Convert absolute arXiv URLs to relative anchors
        if "arxiv.org/html/" in href and "#" in href:
            ref["href"] = "#" + href.split("#")[-1]

    # 8. Handle citation references
    for cite in soup_fragment.select(".ltx_cite"):
        existing = cite.get("class", [])
        if "citation" not in existing:
            cite["class"] = existing + ["citation"]

    return str(soup_fragment), footnotes


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract paper title."""
    # Try LaTeXML title class
    title_elem = soup.select_one(".ltx_title.ltx_title_document")
    if title_elem:
        return _clean_text(title_elem.get_text())

    # Fallback to h1
    h1 = soup.find("h1")
    if h1:
        return _clean_text(h1.get_text())

    # Last resort: page title
    title_tag = soup.find("title")
    if title_tag:
        return _clean_text(title_tag.get_text())

    return "Untitled Paper"


def _extract_authors(soup: BeautifulSoup) -> list[str]:
    """Extract author names."""
    authors = []

    # Try LaTeXML author elements
    author_elems = soup.select(".ltx_personname")
    if author_elems:
        for elem in author_elems:
            # Get direct text content, excluding nested elements with emails
            # First try to get text before any <br> or email-containing spans
            name_parts = []
            for child in elem.children:
                if isinstance(child, NavigableString):
                    text = str(child).strip()
                    if text and "@" not in text:
                        name_parts.append(text)
                elif isinstance(child, Tag):
                    # Skip elements that contain emails
                    child_text = child.get_text()
                    if "@" not in child_text and child.name not in ["br"]:
                        name_parts.append(_clean_text(child_text))

            name = " ".join(name_parts).strip()

            # Fallback to full text if no parts found
            if not name:
                full_text = _clean_text(elem.get_text())
                # Try to extract name before email
                if "@" in full_text:
                    # Split on common email patterns
                    name = full_text.split("@")[0].rsplit(" ", 1)[0].strip()
                else:
                    name = full_text

            if name and name not in authors and len(name) < 100:
                authors.append(name)
        return authors

    # Try meta tags
    meta_authors = soup.select('meta[name="citation_author"]')
    for meta in meta_authors:
        content = meta.get("content", "")
        if content:
            authors.append(content)

    return authors


def _extract_abstract(soup: BeautifulSoup) -> str:
    """Extract paper abstract."""
    # Try LaTeXML abstract
    abstract_elem = soup.select_one(".ltx_abstract")
    if abstract_elem:
        # Get text content, skip the "Abstract" heading
        paragraphs = abstract_elem.select("p")
        if paragraphs:
            return " ".join(_clean_text(p.get_text()) for p in paragraphs)
        return _clean_text(abstract_elem.get_text())

    # Try meta description
    meta_desc = soup.select_one('meta[name="description"]')
    if meta_desc:
        return meta_desc.get("content", "")

    return ""


def _extract_date(soup: BeautifulSoup) -> str | None:
    """Extract publication date."""
    # Try meta tag
    meta_date = soup.select_one('meta[name="citation_date"]')
    if meta_date:
        return meta_date.get("content")

    # Try LaTeXML date
    date_elem = soup.select_one(".ltx_date")
    if date_elem:
        return _clean_text(date_elem.get_text())

    return None


def _extract_sections(soup: BeautifulSoup) -> tuple[list[Section], list[Footnote]]:
    """Extract paper sections with their content and footnotes."""
    sections = []
    all_footnotes: list[Footnote] = []
    footnote_counter = [0]  # Mutable counter for footnotes

    # Find all LaTeXML sections
    section_elems = soup.select(".ltx_section, .ltx_subsection, .ltx_subsubsection")

    for i, elem in enumerate(section_elems):
        # Determine section level
        classes = elem.get("class", [])
        if "ltx_section" in classes:
            level = 1
        elif "ltx_subsection" in classes:
            level = 2
        else:
            level = 3

        # Get section ID
        section_id = elem.get("id", f"section-{i}")

        # Get title
        title_elem = elem.select_one(".ltx_title")
        title = _clean_text(title_elem.get_text()) if title_elem else f"Section {i + 1}"

        # Create a container for content to process
        content_container = soup.new_tag("div")

        for child in list(elem.children):
            if isinstance(child, Tag):
                child_classes = child.get("class", [])
                # Skip the title element
                if "ltx_title" in child_classes:
                    continue
                # Skip nested sections - they'll be processed separately
                if any(
                    cls in child_classes
                    for cls in ["ltx_section", "ltx_subsection", "ltx_subsubsection"]
                ):
                    continue
                # Clone the child to avoid modifying original
                content_container.append(child)

        # Process content (extract footnotes, wrap tables, etc.)
        processed_html, section_footnotes = _process_content(content_container, footnote_counter)
        all_footnotes.extend(section_footnotes)

        sections.append(
            Section(
                id=section_id,
                title=title,
                level=level,
                content=processed_html,
            )
        )

    # If no LaTeXML sections found, try to get main content
    if not sections:
        main_content = soup.select_one(".ltx_page_main, .ltx_page_content, article, main, .content")
        if main_content:
            container = soup.new_tag("div")
            for child in list(main_content.children):
                if isinstance(child, Tag):
                    container.append(child)

            processed_html, section_footnotes = _process_content(container, footnote_counter)
            all_footnotes.extend(section_footnotes)

            sections.append(
                Section(
                    id="main-content",
                    title="Content",
                    level=1,
                    content=processed_html,
                )
            )

    return sections, all_footnotes


def _extract_figures(soup: BeautifulSoup, base_url: str | None = None) -> list[Figure]:
    """Extract figures from the paper."""
    figures = []

    figure_elems = soup.select(".ltx_figure, figure")

    for i, elem in enumerate(figure_elems):
        fig_id = elem.get("id", f"figure-{i}")

        # Get caption
        caption_elem = elem.select_one(".ltx_caption, figcaption")
        caption = _clean_text(caption_elem.get_text()) if caption_elem else ""

        # Get image URL
        img = elem.select_one("img")
        image_url = None
        if img:
            src = img.get("src", "")
            if src:
                if base_url:
                    image_url = urljoin(base_url, src)
                else:
                    image_url = src

        figures.append(
            Figure(
                id=fig_id,
                caption=caption,
                image_url=image_url,
            )
        )

    return figures


def _extract_all_images(soup: BeautifulSoup, base_url: str | None = None) -> dict[str, str]:
    """Extract ALL image URLs from the HTML and return a mapping of original to absolute URLs.

    This finds images everywhere - in figures, inline, tables, etc.
    """
    image_map = {}

    # Find all img tags anywhere in the document
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src and not src.startswith("data:"):  # Skip data URIs
            if base_url:
                absolute_url = urljoin(base_url, src)
            else:
                absolute_url = src
            # Map original src to absolute URL
            image_map[src] = absolute_url

    # Also find SVG images that might be linked
    for svg_use in soup.select("use[href], use[xlink\\:href]"):
        href = svg_use.get("href") or svg_use.get("xlink:href", "")
        if href and not href.startswith("#") and not href.startswith("data:"):
            if base_url:
                absolute_url = urljoin(base_url, href)
            else:
                absolute_url = href
            image_map[href] = absolute_url

    return image_map


def _extract_references(soup: BeautifulSoup) -> str | None:
    """Extract references section HTML."""
    refs = soup.select_one(".ltx_bibliography, #references, .references")
    if refs:
        # Clean up the references for EPUB
        # Convert absolute URLs to relative anchors
        for ref in refs.select(".ltx_ref"):
            href = ref.get("href", "")
            if "arxiv.org/html/" in href and "#" in href:
                ref["href"] = "#" + href.split("#")[-1]
        return str(refs)
    return None


def parse_paper(html: str, paper_id: str, base_url: str | None = None) -> Paper:
    """Parse arXiv HTML into a Paper object.

    Args:
        html: HTML content of the paper
        paper_id: arXiv paper ID
        base_url: Base URL for resolving relative image URLs

    Returns:
        Parsed Paper object
    """
    soup = BeautifulSoup(html, "lxml")

    # Set base URL from paper ID if not provided
    if not base_url:
        base_url = f"https://arxiv.org/html/{paper_id}/"

    # Extract figures and images BEFORE sections (since section extraction modifies soup)
    figures = _extract_figures(soup, base_url)
    all_images = _extract_all_images(soup, base_url)

    # Now extract sections (this may modify the soup)
    sections, footnotes = _extract_sections(soup)

    return Paper(
        id=paper_id,
        title=_extract_title(soup),
        authors=_extract_authors(soup),
        abstract=_extract_abstract(soup),
        date=_extract_date(soup),
        sections=sections,
        figures=figures,
        footnotes=footnotes,
        references_html=_extract_references(soup),
        base_url=base_url,
        all_images=all_images,
    )
