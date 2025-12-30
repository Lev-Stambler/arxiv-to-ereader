"""Convert parsed papers to EPUB and Kindle formats."""

import re
import shutil
import subprocess
import tempfile
import zipfile
from enum import Enum
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from ebooklib import epub

from arxiv_to_ereader.math_renderer import MathImage, render_latex_to_image
from arxiv_to_ereader.parser import Paper
from arxiv_to_ereader.styles import get_cover_css, get_stylesheet


class OutputFormat(str, Enum):
    """Supported output formats."""

    EPUB = "epub"
    MOBI = "mobi"
    AZW3 = "azw3"


def _check_calibre_available() -> bool:
    """Check if Calibre's ebook-convert is available."""
    return shutil.which("ebook-convert") is not None


def _scrub_epub_for_kindle(epub_path: Path) -> None:
    """Scrub EPUB for Kindle compatibility without requiring Calibre.

    Amazon's Send to Kindle is stricter than standard readers. This function
    applies fixes based on kindle-epub-fix (https://github.com/innocenat/kindle-epub-fix):

    1. Add UTF-8 encoding declarations (Amazon assumes ISO-8859-1 otherwise)
    2. Fix NCX links pointing to body IDs (Amazon rejects these)
    3. Ensure dc:language metadata exists
    4. Remove <img> tags without src attributes
    5. Strip MathML elements (Kindle doesn't support them; keeps alttext as fallback)
    6. Remove empty <ol/> tags (invalid in EPUB nav)

    Args:
        epub_path: Path to the EPUB file to scrub (modified in place)
    """
    # Read all files from the EPUB
    files_content: dict[str, bytes] = {}
    with zipfile.ZipFile(epub_path, "r") as zf:
        for name in zf.namelist():
            files_content[name] = zf.read(name)

    # Track body IDs for NCX fix
    body_ids: dict[str, str] = {}  # filename -> body_id

    # Process each file
    for name, content in list(files_content.items()):
        if name == "mimetype":
            continue

        # Process XML/HTML files
        if name.endswith((".xhtml", ".html", ".xml", ".opf", ".ncx")):
            try:
                text = content.decode("utf-8")
                modified = False

                # Fix 1: Ensure UTF-8 encoding declaration
                if text.lstrip().startswith("<?xml"):
                    # Replace existing declaration to ensure UTF-8 is explicit
                    new_text = re.sub(
                        r"<\?xml[^?]*\?>",
                        '<?xml version="1.0" encoding="utf-8"?>',
                        text,
                        count=1,
                    )
                    if new_text != text:
                        text = new_text
                        modified = True
                elif not text.lstrip().startswith("<!DOCTYPE"):
                    # Add declaration if missing
                    text = '<?xml version="1.0" encoding="utf-8"?>\n' + text
                    modified = True

                # Remove invalid XML control characters
                cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
                if cleaned != text:
                    text = cleaned
                    modified = True

                # Process XHTML files for Kindle compatibility
                if name.endswith((".xhtml", ".html")):
                    soup = BeautifulSoup(text, "lxml-xml")
                    soup_modified = False

                    # Find body ID for NCX fix
                    body = soup.find("body")
                    if body and body.get("id"):
                        # Extract just the filename without path
                        filename = name.split("/")[-1]
                        body_ids[filename] = body["id"]

                    # Fix 4: Remove img tags without src
                    for img in soup.find_all("img"):
                        if not img.get("src"):
                            img.decompose()
                            soup_modified = True

                    # Fix 5: Strip MathML (Kindle doesn't support it)
                    # Replace with alttext or empty string as fallback
                    for math in soup.find_all("math"):
                        alt = math.get("alttext", "")
                        if alt:
                            math.replace_with(f" {alt} ")
                        else:
                            math.decompose()
                        soup_modified = True

                    # Fix 6: Remove empty <ol/> tags (invalid in EPUB nav)
                    for ol in soup.find_all("ol"):
                        if not ol.find("li"):
                            ol.decompose()
                            soup_modified = True

                    if soup_modified:
                        # Only re-serialize if we actually modified something
                        text = str(soup)
                        modified = True

                # Fix 3: Ensure dc:language exists (for OPF files)
                if name.endswith(".opf"):
                    if "<dc:language>" not in text and "<dc:language/>" not in text:
                        # Add language after metadata opening tag
                        text = re.sub(
                            r"(<metadata[^>]*>)",
                            r'\1\n    <dc:language>en</dc:language>',
                            text,
                            count=1,
                        )
                        modified = True

                if modified:
                    files_content[name] = text.encode("utf-8")

            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

    # Fix 2: Fix NCX links pointing to body IDs
    for name, content in list(files_content.items()):
        if name.endswith(".ncx"):
            try:
                text = content.decode("utf-8")
                modified = False

                for filename, body_id in body_ids.items():
                    # Replace links like "file.xhtml#bodyId" with "file.xhtml"
                    pattern = f'src="{filename}#{body_id}"'
                    replacement = f'src="{filename}"'
                    if pattern in text:
                        text = text.replace(pattern, replacement)
                        modified = True

                    # Also check with path prefixes
                    pattern_with_path = f'src="[^"]*/{filename}#{body_id}"'
                    if re.search(pattern_with_path, text):
                        text = re.sub(
                            f'src="([^"]*)/{filename}#{body_id}"',
                            f'src="\\1/{filename}"',
                            text,
                        )
                        modified = True

                if modified:
                    files_content[name] = text.encode("utf-8")
            except (UnicodeDecodeError, UnicodeEncodeError):
                pass

    # Rewrite the EPUB with proper structure
    # mimetype must be first and uncompressed
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as zf:
        # Write mimetype first, uncompressed
        if "mimetype" in files_content:
            zf.writestr("mimetype", files_content["mimetype"], compress_type=zipfile.ZIP_STORED)

        # Write all other files
        for name, content in files_content.items():
            if name != "mimetype":
                zf.writestr(name, content)


def _convert_epub_to_kindle(
    epub_path: Path,
    output_path: Path,
    output_format: OutputFormat,
) -> Path:
    """Convert EPUB to Kindle format using Calibre's ebook-convert.

    Args:
        epub_path: Path to the source EPUB file
        output_path: Path for the output file
        output_format: Target format (mobi or azw3)

    Returns:
        Path to the converted file

    Raises:
        RuntimeError: If Calibre is not installed or conversion fails
    """
    if not _check_calibre_available():
        raise RuntimeError(
            "Calibre's ebook-convert not found. Install Calibre to convert to Kindle formats.\n"
            "  - macOS: brew install calibre\n"
            "  - Ubuntu/Debian: sudo apt install calibre\n"
            "  - Or download from: https://calibre-ebook.com/download"
        )

    try:
        result = subprocess.run(
            ["ebook-convert", str(epub_path), str(output_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Calibre conversion failed: {e.stderr}") from e

    return output_path


def _create_cover_chapter(paper: Paper) -> epub.EpubHtml:
    """Create a cover/title page chapter."""
    authors_html = ", ".join(paper.authors) if paper.authors else "Unknown Authors"
    date_html = f"<p class='date'>{paper.date}</p>" if paper.date else ""

    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{paper.title}</title>
    <style>{get_cover_css()}</style>
</head>
<body>
    <h1>{paper.title}</h1>
    <p class="authors">{authors_html}</p>
    {date_html}
    <p class="paper-id">arXiv:{paper.id}</p>
</body>
</html>"""

    chapter = epub.EpubHtml(title="Cover", file_name="cover.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    return chapter


def _create_abstract_chapter(paper: Paper, stylesheet: epub.EpubItem) -> epub.EpubHtml:
    """Create an abstract chapter."""
    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Abstract</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <div class="abstract">
        <p class="abstract-title">Abstract</p>
        <p>{paper.abstract}</p>
    </div>
</body>
</html>"""

    chapter = epub.EpubHtml(title="Abstract", file_name="abstract.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _create_section_chapter(
    section_idx: int,
    title: str,
    content: str,
    stylesheet: epub.EpubItem,
) -> epub.EpubHtml:
    """Create a chapter from a paper section."""
    html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>"""

    chapter = epub.EpubHtml(
        title=title,
        file_name=f"section_{section_idx:02d}.xhtml",
        lang="en",
    )
    chapter.content = html_content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _create_references_chapter(
    references_html: str,
    stylesheet: epub.EpubItem,
) -> epub.EpubHtml:
    """Create a references chapter."""
    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>References</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>References</h1>
    {references_html}
</body>
</html>"""

    chapter = epub.EpubHtml(title="References", file_name="references.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _create_footnotes_chapter(
    footnotes: list,
    stylesheet: epub.EpubItem,
) -> epub.EpubHtml:
    """Create a footnotes chapter."""
    from arxiv_to_ereader.parser import Footnote

    footnotes_html = ""
    for fn in footnotes:
        if isinstance(fn, Footnote):
            back_link = f'<a href="#fnref-{fn.index}" class="footnote-back">↩</a>'
            footnotes_html += f'<li id="{fn.id}">{fn.content} {back_link}</li>\n'

    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Notes</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <section class="footnotes-section" epub:type="footnotes">
        <h1>Notes</h1>
        <ol>
            {footnotes_html}
        </ol>
    </section>
</body>
</html>"""

    chapter = epub.EpubHtml(title="Notes", file_name="footnotes.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _convert_math_to_images(
    html_content: str,
    math_images: dict[str, MathImage],
    dpi: int = 150,
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

    # Find all <math> elements
    math_elements = soup.find_all("math")

    for math_elem in math_elements:
        # Get display type (block vs inline)
        display = math_elem.get("display", "inline")
        is_display = display == "block"

        # Extract LaTeX from alttext or annotation
        latex = None
        alttext = math_elem.get("alttext")
        if alttext:
            latex = alttext
        else:
            # Try annotation element
            annotation = math_elem.select_one('annotation[encoding="application/x-tex"]')
            if annotation:
                latex = annotation.get_text()

        if not latex:
            continue

        # Check if we already rendered this equation
        if latex in math_images:
            math_img = math_images[latex]
        else:
            # Render to image
            math_img = render_latex_to_image(latex, dpi=dpi, is_display=is_display)
            if math_img:
                math_images[latex] = math_img

        if math_img:
            # Create img tag to replace math
            img_tag = soup.new_tag("img")
            img_tag["src"] = f"math/{math_img.filename}"
            img_tag["alt"] = latex[:200] if len(latex) > 200 else latex
            img_tag["class"] = "math-image math-display" if is_display else "math-image math-inline"

            # For display equations, wrap in a div for proper centering
            if is_display:
                wrapper = soup.new_tag("div")
                wrapper["class"] = "math-block-img"
                wrapper.append(img_tag)
                math_elem.replace_with(wrapper)
            else:
                # For inline math, add vertical-align style for baseline alignment
                if math_img.depth_em != 0:
                    img_tag["style"] = f"vertical-align: {math_img.depth_em:.2f}em;"
                math_elem.replace_with(img_tag)

    # Return the modified HTML
    # Extract just the body content if wrapped by lxml
    body = soup.find("body")
    if body:
        return "".join(str(child) for child in body.children), math_images
    return str(soup), math_images


def _download_image(url: str, timeout: float = 30.0) -> tuple[bytes, str] | None:
    """Download an image and return its content and media type.

    Returns:
        Tuple of (image_bytes, media_type) or None if download fails
    """
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


def convert_to_epub(
    paper: Paper,
    output_path: Path | str | None = None,
    style_preset: str = "default",
    download_images: bool = True,
    output_format: OutputFormat | str = OutputFormat.EPUB,
    render_math: bool = True,
    math_dpi: int = 150,
) -> Path:
    """Convert a parsed paper to EPUB or Kindle format.

    Args:
        paper: Parsed Paper object
        output_path: Output file path (defaults to {paper_id}.{format} in current directory)
        style_preset: Style preset name ("default", "compact", "large-text")
        download_images: Whether to download and embed images
        output_format: Output format ("epub", "mobi", or "azw3")
        render_math: Whether to convert math equations to images (recommended for Kindle)
        math_dpi: DPI resolution for rendered math images

    Returns:
        Path to the created ebook file
    """
    # Normalize format
    if isinstance(output_format, str):
        output_format = OutputFormat(output_format.lower())
    # Create EPUB book
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f"arxiv:{paper.id}")
    book.set_title(paper.title)
    book.set_language("en")

    for i, author in enumerate(paper.authors):
        book.add_author(author, uid=f"creator_{i}")

    if paper.date:
        book.add_metadata("DC", "date", paper.date)

    book.add_metadata("DC", "source", f"https://arxiv.org/abs/{paper.id}")
    book.add_metadata("DC", "publisher", "arXiv")

    # Create stylesheet
    stylesheet = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=get_stylesheet(style_preset),
    )
    book.add_item(stylesheet)

    # Create chapters
    chapters = []

    # Cover page
    cover_chapter = _create_cover_chapter(paper)
    book.add_item(cover_chapter)
    chapters.append(cover_chapter)

    # Abstract
    if paper.abstract:
        abstract_chapter = _create_abstract_chapter(paper, stylesheet)
        book.add_item(abstract_chapter)
        chapters.append(abstract_chapter)

    # Download and add ALL images from the paper
    # Maps original src (relative or absolute) -> epub path
    image_url_to_epub_path: dict[str, str] = {}

    if download_images and paper.all_images:
        for i, (original_src, absolute_url) in enumerate(paper.all_images.items()):
            result = _download_image(absolute_url)
            if result:
                img_data, media_type = result
                # Create a safe filename
                ext = media_type.split("/")[-1]
                if ext == "jpeg":
                    ext = "jpg"
                elif ext == "svg+xml":
                    ext = "svg"

                # Use index to ensure unique filenames
                img_filename = f"images/img_{i:04d}.{ext}"

                img_item = epub.EpubItem(
                    uid=f"image_{i}",
                    file_name=img_filename,
                    media_type=media_type,
                    content=img_data,
                )
                book.add_item(img_item)

                # Map both original src and absolute URL to the epub path
                image_url_to_epub_path[original_src] = img_filename
                image_url_to_epub_path[absolute_url] = img_filename

    # Track rendered math images across all sections
    math_images: dict[str, MathImage] = {}

    # Sections
    for i, section in enumerate(paper.sections):
        # Update image URLs in section content
        content = section.content
        for old_url, new_path in image_url_to_epub_path.items():
            # Replace in both quote styles
            content = content.replace(f'src="{old_url}"', f'src="{new_path}"')
            content = content.replace(f"src='{old_url}'", f"src='{new_path}'")

        # Convert math to images if enabled
        if render_math:
            content, math_images = _convert_math_to_images(content, math_images, dpi=math_dpi)

        section_chapter = _create_section_chapter(
            i,
            section.title,
            content,
            stylesheet,
        )
        book.add_item(section_chapter)
        chapters.append(section_chapter)

    # Add all rendered math images to the EPUB
    if render_math and math_images:
        for math_img in math_images.values():
            img_item = epub.EpubItem(
                uid=f"math_{math_img.filename.replace('.', '_')}",
                file_name=f"math/{math_img.filename}",
                media_type=math_img.image_type,
                content=math_img.image_data,
            )
            book.add_item(img_item)

    # References
    if paper.references_html:
        refs_chapter = _create_references_chapter(paper.references_html, stylesheet)
        book.add_item(refs_chapter)
        chapters.append(refs_chapter)

    # Footnotes (if any were extracted)
    if paper.footnotes:
        footnotes_chapter = _create_footnotes_chapter(paper.footnotes, stylesheet)
        book.add_item(footnotes_chapter)
        chapters.append(footnotes_chapter)

    # Create table of contents
    book.toc = [(chapter, []) for chapter in chapters]

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set spine (reading order)
    book.spine = ["nav"] + chapters

    # Determine output path
    file_ext = output_format.value
    if output_path is None:
        output_path = Path(f"{paper.id.replace('/', '_')}.{file_ext}")
    else:
        output_path = Path(output_path)
        # Update extension if format specified but path has wrong extension
        if output_path.suffix.lower() != f".{file_ext}":
            output_path = output_path.with_suffix(f".{file_ext}")

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # For Kindle formats, we need to first create an EPUB then convert
    if output_format in (OutputFormat.MOBI, OutputFormat.AZW3):
        # Create temporary EPUB
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp_epub_path = Path(tmp.name)

        try:
            epub.write_epub(str(tmp_epub_path), book, {})
            _scrub_epub_for_kindle(tmp_epub_path)
            _convert_epub_to_kindle(tmp_epub_path, output_path, output_format)
        finally:
            # Clean up temp file
            tmp_epub_path.unlink(missing_ok=True)
    else:
        # Write EPUB directly and scrub for Kindle compatibility
        epub.write_epub(str(output_path), book, {})
        _scrub_epub_for_kindle(output_path)

    return output_path
