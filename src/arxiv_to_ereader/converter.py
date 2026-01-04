"""Convert parsed papers to PDF format optimized for e-readers."""

import base64
from io import BytesIO
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from weasyprint import CSS, HTML

from arxiv_to_ereader.math_renderer import MathImage, render_latex_to_image
from arxiv_to_ereader.parser import Paper
from arxiv_to_ereader.screen_presets import ScreenPreset, custom_preset, get_preset
from arxiv_to_ereader.styles import get_pdf_stylesheet


def _convert_math_to_images(
    html_content: str,
    math_images: dict[str, MathImage],
    dpi: int = 200,
) -> tuple[str, dict[str, MathImage]]:
    """Convert all math elements in HTML content to images.

    Finds MathML elements, extracts their LaTeX, renders to images,
    and replaces them with <img> tags.

    Args:
        html_content: HTML content with math elements
        math_images: Dictionary to accumulate rendered math images (modified in place)
        dpi: Resolution for rendered math images

    Returns:
        Tuple of (modified_html, math_images)
    """
    soup = BeautifulSoup(html_content, "lxml")

    for math_elem in soup.find_all("math"):
        display = math_elem.get("display", "inline")
        is_display = display == "block"

        # Extract LaTeX from alttext or annotation
        latex = None
        alttext = math_elem.get("alttext")
        if alttext:
            latex = alttext
        else:
            annotation = math_elem.select_one('annotation[encoding="application/x-tex"]')
            if annotation:
                latex = annotation.get_text()

        if not latex:
            continue

        # Check if we already rendered this equation
        if latex in math_images:
            math_img = math_images[latex]
        else:
            math_img = render_latex_to_image(latex, dpi=dpi, is_display=is_display)
            if math_img:
                math_images[latex] = math_img

        if math_img:
            # Create img tag with base64 data URI
            b64_data = base64.b64encode(math_img.image_data).decode("ascii")
            img_tag = soup.new_tag("img")
            img_tag["src"] = f"data:{math_img.image_type};base64,{b64_data}"
            img_tag["alt"] = latex[:200] if len(latex) > 200 else latex
            img_tag["class"] = "math-image math-display" if is_display else "math-image math-inline"

            if is_display:
                wrapper = soup.new_tag("div")
                wrapper["class"] = "math-block-img"
                wrapper.append(img_tag)
                math_elem.replace_with(wrapper)
            else:
                style_parts = [
                    "display: inline",
                    "height: 1em",
                    "max-height: 1.3em",
                    "width: auto",
                    "margin: 0",
                ]
                if math_img.depth_em != 0:
                    style_parts.append(f"vertical-align: {math_img.depth_em:.2f}em")
                img_tag["style"] = "; ".join(style_parts) + ";"
                math_elem.replace_with(img_tag)

    body = soup.find("body")
    if body:
        return "".join(str(child) for child in body.children), math_images
    return str(soup), math_images


def _download_image(url: str, timeout: float = 30.0) -> tuple[bytes, str] | None:
    """Download an image and return its content and media type."""
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/png")
            if ";" in content_type:
                content_type = content_type.split(";")[0].strip()

            return response.content, content_type
    except Exception:
        return None


def _build_html_document(
    paper: Paper,
    image_map: dict[str, str],
    render_math: bool = True,
    math_dpi: int = 200,
) -> str:
    """Build a complete HTML document from the Paper object.

    Args:
        paper: Parsed Paper object
        image_map: Map of original image URLs to base64 data URIs
        render_math: Whether to convert math to images
        math_dpi: DPI for math images

    Returns:
        Complete HTML document as string
    """
    math_images: dict[str, MathImage] = {}

    # Build sections HTML
    sections_html = ""
    for section in paper.sections:
        content = section.content

        # Replace image URLs with base64 data URIs
        for old_url, new_src in image_map.items():
            content = content.replace(f'src="{old_url}"', f'src="{new_src}"')
            content = content.replace(f"src='{old_url}'", f"src='{new_src}'")

        # Convert math to images if enabled
        if render_math:
            content, math_images = _convert_math_to_images(content, math_images, dpi=math_dpi)

        level = min(section.level + 1, 6)
        sections_html += f"""
        <section id="{section.id}">
            <h{level}>{section.title}</h{level}>
            {content}
        </section>
        """

    # Build complete document
    authors_html = ", ".join(paper.authors) if paper.authors else "Unknown"
    date_html = f'<p class="date">{paper.date}</p>' if paper.date else ""

    abstract_html = ""
    if paper.abstract:
        abstract_html = f"""
        <div class="abstract">
            <p class="abstract-title">Abstract</p>
            <p>{paper.abstract}</p>
        </div>
        """

    references_html = ""
    if paper.references_html:
        refs_content = paper.references_html
        for old_url, new_src in image_map.items():
            refs_content = refs_content.replace(f'src="{old_url}"', f'src="{new_src}"')
        # Convert math in references
        if render_math:
            refs_content, math_images = _convert_math_to_images(refs_content, math_images, dpi=math_dpi)
        references_html = f"""
        <section class="references">
            <h2>References</h2>
            {refs_content}
        </section>
        """

    footnotes_html = ""
    if paper.footnotes:
        footnotes_items = []
        for fn in paper.footnotes:
            fn_content = fn.content
            # Convert math in footnotes
            if render_math:
                fn_content, math_images = _convert_math_to_images(fn_content, math_images, dpi=math_dpi)
            footnotes_items.append(
                f'<li id="{fn.id}">{fn_content} <a href="#fnref-{fn.index}" class="footnote-back">^</a></li>'
            )
        footnotes_list = "\n".join(footnotes_items)
        footnotes_html = f"""
        <section class="footnotes-section">
            <h2>Notes</h2>
            <ol>{footnotes_list}</ol>
        </section>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <title>{paper.title}</title>
</head>
<body>
    <div class="cover">
        <h1>{paper.title}</h1>
        <p class="authors">{authors_html}</p>
        {date_html}
        <p class="paper-id">arXiv:{paper.id}</p>
    </div>

    {abstract_html}

    {sections_html}

    {references_html}

    {footnotes_html}
</body>
</html>
"""
    return html


def convert_to_pdf(
    paper: Paper,
    output_path: Path | str | None = None,
    screen_preset: str = "kindle-paperwhite",
    custom_width_mm: float | None = None,
    custom_height_mm: float | None = None,
    download_images: bool = True,
    render_math: bool = True,
    math_dpi: int = 200,
) -> Path:
    """Convert a parsed paper to PDF format optimized for e-readers.

    Args:
        paper: Parsed Paper object
        output_path: Output file path (defaults to {paper_id}.pdf)
        screen_preset: Screen size preset name
        custom_width_mm: Custom page width in mm (overrides preset)
        custom_height_mm: Custom page height in mm (overrides preset)
        download_images: Whether to download and embed images
        render_math: Whether to convert math equations to images
        math_dpi: DPI for rendered math images

    Returns:
        Path to the created PDF file
    """
    # Get screen preset
    if custom_width_mm and custom_height_mm:
        preset = custom_preset(custom_width_mm, custom_height_mm)
    else:
        preset = get_preset(screen_preset)

    # Download images and create base64 data URI map
    image_map: dict[str, str] = {}
    if download_images and paper.all_images:
        for original_src, absolute_url in paper.all_images.items():
            result = _download_image(absolute_url)
            if result:
                img_data, media_type = result
                b64_data = base64.b64encode(img_data).decode("ascii")
                data_uri = f"data:{media_type};base64,{b64_data}"
                image_map[original_src] = data_uri
                image_map[absolute_url] = data_uri

    # Build HTML document
    html_content = _build_html_document(
        paper,
        image_map,
        render_math=render_math,
        math_dpi=math_dpi,
    )

    # Get CSS
    css_content = get_pdf_stylesheet(preset)

    # Determine output path
    if output_path is None:
        output_path = Path(f"{paper.id.replace('/', '_')}.pdf")
    else:
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate PDF with WeasyPrint
    html = HTML(string=html_content, base_url=paper.base_url)
    css = CSS(string=css_content)
    html.write_pdf(str(output_path), stylesheets=[css])

    return output_path
