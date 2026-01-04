"""Convert parsed papers to EPUB format."""

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import httpx
from bs4 import BeautifulSoup
from ebooklib import epub

from arxiv_to_ereader.math_renderer import MathImage, render_latex_to_image
from arxiv_to_ereader.parser import Footnote, Paper
from arxiv_to_ereader.styles import get_cover_css, get_stylesheet


def _collect_ids_from_html(html_content: str) -> set[str]:
    """Collect all element IDs from HTML content."""
    if not html_content:
        return set()
    soup = BeautifulSoup(html_content, "lxml")
    return {elem["id"] for elem in soup.find_all(attrs={"id": True})}


def _rewrite_internal_links(
    html_content: str,
    current_filename: str,
    id_to_filename: dict[str, str],
) -> str:
    """Rewrite internal links to point to the correct file.

    When content is split across multiple XHTML files, links like #bib.bibx9
    must become references.xhtml#bib.bibx9 to work correctly in EPUBs.
    """
    if not html_content:
        return html_content

    soup = BeautifulSoup(html_content, "lxml")
    modified = False

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("#") and len(href) > 1:
            target_id = href[1:]
            if target_id in id_to_filename:
                target_file = id_to_filename[target_id]
                # Only rewrite if target is in a different file
                if target_file != current_filename:
                    a["href"] = f"{target_file}#{target_id}"
                    modified = True

    if modified:
        # Return content without <html><body> wrappers if they were added by parser
        body = soup.find("body")
        if body:
            return "".join(str(child) for child in body.children)
        return str(soup)

    return html_content


def validate_epub(epub_path: Path) -> tuple[bool, list[str]]:
    """Validate an EPUB file using EPUBCheck if available.

    Args:
        epub_path: Path to the EPUB file to validate

    Returns:
        Tuple of (is_valid, error_messages).
        If EPUBCheck is not available, returns (True, []) to avoid blocking.
    """
    # Try to find epubcheck - check common locations
    epubcheck_jar = None

    # Check environment variable first
    import os

    env_jar = os.environ.get("EPUBCHECK_JAR")
    if env_jar and Path(env_jar).exists():
        epubcheck_jar = Path(env_jar)

    # Check common installation paths
    if not epubcheck_jar:
        common_paths = [
            Path("/tmp/epubcheck-5.1.0/epubcheck.jar"),
            Path.home() / ".local" / "share" / "epubcheck" / "epubcheck.jar",
            Path("/usr/share/java/epubcheck.jar"),
        ]
        for path in common_paths:
            if path.exists():
                epubcheck_jar = path
                break

    # Check if java is available
    if shutil.which("java") is None:
        return True, []  # Can't validate without Java

    if epubcheck_jar is None:
        return True, []  # Can't validate without EPUBCheck

    try:
        result = subprocess.run(
            ["java", "-jar", str(epubcheck_jar), str(epub_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = result.stdout + result.stderr

        # Parse errors from output
        errors = []
        for line in output.split("\n"):
            if line.startswith("ERROR") or line.startswith("FATAL"):
                errors.append(line.strip())

        return result.returncode == 0, errors

    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return True, []  # Validation unavailable


def _scrub_epub_for_kindle(epub_path: Path) -> None:
    """Scrub EPUB for Kindle compatibility.

    Amazon officially supports EPUB (since 2022). The main compatibility issues are:
    1. Missing UTF-8 encoding declaration (Amazon assumes ISO-8859-1 otherwise)
    2. NCX links pointing to body IDs with fragment hashes
    3. Missing dc:language metadata
    4. <img> tags without src attributes
    5. Remaining MathML elements (we render to images, but catch any stragglers)
    6. External HTTP(S) links (may cause Send to Kindle rejection)
    7. Anchor tags without href (LaTeXML cross-references break Kindle validation)
    8. Missing citation markers (ltx_missing_citation elements)
    9. Empty <ol> elements (invalid EPUB structure)
    10. Data URLs (not allowed in EPUB)
    11. Broken internal links (fragment identifiers pointing to non-existent IDs)

    Based on: https://kindle-epub-fix.netlify.app/

    Args:
        epub_path: Path to the EPUB file to scrub (modified in place)
    """
    files_content: dict[str, bytes] = {}
    with zipfile.ZipFile(epub_path, "r") as zf:
        for name in zf.namelist():
            files_content[name] = zf.read(name)

    # Track body IDs for NCX fix
    body_ids: dict[str, str] = {}  # filename -> body_id

    # Collect all IDs from all XHTML files for broken link detection
    all_ids: dict[str, set[str]] = {}  # filename -> set of IDs
    for name, content in files_content.items():
        if name.endswith((".xhtml", ".html")):
            try:
                text = content.decode("utf-8")
                soup = BeautifulSoup(text, "lxml")
                filename = name.split("/")[-1]
                all_ids[filename] = {elem["id"] for elem in soup.find_all(attrs={"id": True})}
            except (UnicodeDecodeError, Exception):
                pass

    for name, content in list(files_content.items()):
        if name == "mimetype":
            continue

        if name.endswith((".xhtml", ".html", ".xml", ".opf", ".ncx")):
            try:
                text = content.decode("utf-8")
                modified = False

                # Fix 1: Ensure UTF-8 encoding declaration
                if not text.lstrip().startswith("<?xml"):
                    text = '<?xml version="1.0" encoding="utf-8"?>\n' + text
                    modified = True
                elif 'encoding=' not in text.split('?>')[0]:
                    text = re.sub(
                        r"<\?xml([^?]*)\?>",
                        '<?xml version="1.0" encoding="utf-8"?>',
                        text,
                        count=1,
                    )
                    modified = True

                # Remove invalid XML control characters
                cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
                if cleaned != text:
                    text = cleaned
                    modified = True

                # Process XHTML files
                if name.endswith((".xhtml", ".html")):
                    soup = BeautifulSoup(text, "lxml-xml")
                    soup_modified = False

                    # Track body ID for NCX fix
                    body = soup.find("body")
                    if body and body.get("id"):
                        filename = name.split("/")[-1]
                        body_ids[filename] = body["id"]

                    # Fix 4: Remove img tags without src
                    for img in soup.find_all("img"):
                        if not img.get("src"):
                            img.decompose()
                            soup_modified = True

                    # Fix 5: Strip any remaining MathML (should already be images)
                    for math in soup.find_all("math"):
                        alt = math.get("alttext", "")
                        if alt:
                            math.replace_with(f" {alt} ")
                        else:
                            math.decompose()
                        soup_modified = True

                    # Fix 6: Remove external HTTP(S) links (may cause Kindle rejection)
                    for a in soup.find_all("a", href=True):
                        href = a.get("href", "")
                        if href.startswith(("http://", "https://")):
                            # Remove href but keep the link text
                            del a["href"]
                            soup_modified = True

                    # Fix 7: Convert anchor tags without href to spans
                    # LaTeXML generates anchors without href (class ltx_ref) that break Kindle
                    for a in soup.find_all("a"):
                        if not a.get("href"):
                            a.name = "span"
                            # Remove link-specific attributes
                            for attr in ["download", "target", "rel"]:
                                if attr in a.attrs:
                                    del a.attrs[attr]
                            soup_modified = True

                    # Fix 8: Clean up missing citation markers
                    for elem in soup.find_all(class_="ltx_missing_citation"):
                        elem.name = "span"
                        elem["class"] = ["citation-missing"]
                        soup_modified = True

                    # Fix 9: Remove empty <ol> elements (invalid EPUB)
                    for ol in soup.find_all("ol"):
                        if not ol.find_all("li"):
                            ol.decompose()
                            soup_modified = True

                    # Fix 9b: Convert span to div if it contains block elements
                    # arXiv HTML sometimes nests divs inside spans, which is invalid
                    block_elements = {"div", "p", "table", "ul", "ol", "blockquote", "figure", "pre"}
                    for span in soup.find_all("span"):
                        has_block_child = any(
                            child.name in block_elements
                            for child in span.children
                            if hasattr(child, "name")
                        )
                        if has_block_child:
                            span.name = "div"
                            soup_modified = True

                    # Fix 10: Remove data: URLs (not allowed in EPUB)
                    for elem in soup.find_all(attrs={"href": True}):
                        if elem["href"].startswith("data:"):
                            if elem.name == "a":
                                elem.name = "span"
                                # Remove link-specific attributes
                                for attr in ["href", "download", "target", "rel"]:
                                    if attr in elem.attrs:
                                        del elem.attrs[attr]
                            else:
                                del elem["href"]
                            soup_modified = True
                    for elem in soup.find_all(attrs={"src": True}):
                        if elem["src"].startswith("data:"):
                            elem.decompose()
                            soup_modified = True

                    # Fix 11: Remove broken internal links
                    current_file = name.split("/")[-1]
                    for a in soup.find_all("a", href=True):
                        href = a["href"]
                        broken = False
                        if href.startswith("#"):
                            target_id = href[1:]
                            if current_file in all_ids and target_id not in all_ids.get(current_file, set()):
                                # Check if ID exists in any file
                                found = any(target_id in ids for ids in all_ids.values())
                                if not found:
                                    broken = True
                        elif "#" in href and not href.startswith("http"):
                            # Cross-file link like "file.xhtml#id"
                            parts = href.split("#", 1)
                            target_file = parts[0]
                            target_id = parts[1] if len(parts) > 1 else ""
                            if target_id and target_id not in all_ids.get(target_file, set()):
                                broken = True

                        if broken:
                            a.name = "span"
                            for attr in ["href", "download", "target", "rel"]:
                                if attr in a.attrs:
                                    del a.attrs[attr]
                            soup_modified = True

                    if soup_modified:
                        text = str(soup)
                        modified = True

                # Fix 3: Ensure dc:language exists (for OPF files)
                if name.endswith(".opf"):
                    if "<dc:language>" not in text and "<dc:language/>" not in text:
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

    # Rewrite the EPUB (mimetype must be first and uncompressed)
    with zipfile.ZipFile(epub_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if "mimetype" in files_content:
            zf.writestr("mimetype", files_content["mimetype"], compress_type=zipfile.ZIP_STORED)

        for name, content in files_content.items():
            if name != "mimetype":
                zf.writestr(name, content)


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
                # For inline math, add styles for baseline alignment and size constraint
                # These override the base img styles (min-width: 60%, display: block)
                style_parts = [
                    "display: inline",
                    "height: 1em",
                    "max-height: 1.2em",
                    "width: auto",
                    "min-width: 0",
                    "margin: 0",
                ]
                if math_img.depth_em != 0:
                    style_parts.append(f"vertical-align: {math_img.depth_em:.2f}em")
                img_tag["style"] = "; ".join(style_parts) + ";"
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
    render_math: bool = True,
    math_dpi: int = 150,
) -> Path:
    """Convert a parsed paper to EPUB format.

    Args:
        paper: Parsed Paper object
        output_path: Output file path (defaults to {paper_id}.epub in current directory)
        style_preset: Style preset name ("default", "compact", "large-text")
        download_images: Whether to download and embed images
        render_math: Whether to convert math equations to images
        math_dpi: DPI resolution for rendered math images

    Returns:
        Path to the created EPUB file
    """
    # Create EPUB book (EPUB 3 - Amazon officially supports EPUB since 2022)
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

    # Build map of all IDs to their destination filenames for cross-file link fixing
    # This is essential because Amazon's Send to Kindle rejects EPUBs with broken internal links
    id_to_filename: dict[str, str] = {}

    # Map references IDs (e.g., bib.bibx1, bib.bibx2, etc.)
    refs_filename = "references.xhtml"
    if paper.references_html:
        for elem_id in _collect_ids_from_html(paper.references_html):
            id_to_filename[elem_id] = refs_filename

    # Map footnotes IDs (e.g., fn-1, fn-2, etc.)
    footnotes_filename = "footnotes.xhtml"
    if paper.footnotes:
        for fn in paper.footnotes:
            id_to_filename[fn.id] = footnotes_filename

    # Map section IDs and all IDs inside each section
    section_filenames: list[str] = []
    for i, section in enumerate(paper.sections):
        filename = f"section_{i:02d}.xhtml"
        section_filenames.append(filename)

        # Section ID itself
        id_to_filename[section.id] = filename

        # IDs inside the section content
        for elem_id in _collect_ids_from_html(section.content):
            id_to_filename[elem_id] = filename

    # Also add back-reference IDs for footnotes (fnref-X)
    if paper.footnotes:
        for fn in paper.footnotes:
            back_id = f"fnref-{fn.index}"
            # Back-references are in section files, but we don't know which one
            # They'll be rewritten correctly when we process each section

    # Track rendered math images across all sections
    math_images: dict[str, MathImage] = {}

    # Sections
    for i, section in enumerate(paper.sections):
        # Get the filename for this section
        current_filename = section_filenames[i]

        # Update image URLs in section content
        content = section.content
        for old_url, new_path in image_url_to_epub_path.items():
            # Replace in both quote styles
            content = content.replace(f'src="{old_url}"', f'src="{new_path}"')
            content = content.replace(f"src='{old_url}'", f"src='{new_path}'")

        # Fix cross-file internal links (e.g., #bib.bibx9 -> references.xhtml#bib.bibx9)
        content = _rewrite_internal_links(content, current_filename, id_to_filename)

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
        # Rewrite any internal links in references (e.g., back-links to sections)
        refs_html = _rewrite_internal_links(paper.references_html, refs_filename, id_to_filename)
        refs_chapter = _create_references_chapter(refs_html, stylesheet)
        book.add_item(refs_chapter)
        chapters.append(refs_chapter)

    # Footnotes (if any were extracted)
    if paper.footnotes:
        # Rewrite back-links in footnotes to point to correct section files
        rewritten_footnotes = []
        for fn in paper.footnotes:
            rewritten_content = _rewrite_internal_links(fn.content, footnotes_filename, id_to_filename)
            rewritten_footnotes.append(Footnote(id=fn.id, index=fn.index, content=rewritten_content))
        footnotes_chapter = _create_footnotes_chapter(rewritten_footnotes, stylesheet)
        book.add_item(footnotes_chapter)
        chapters.append(footnotes_chapter)

    # Create table of contents (flat list, no empty sub-items)
    book.toc = tuple(chapters)

    # Add navigation files (NCX for compatibility, Nav for EPUB 3)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + chapters

    # Determine output path
    if output_path is None:
        output_path = Path(f"{paper.id.replace('/', '_')}.epub")
    else:
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".epub":
            output_path = output_path.with_suffix(".epub")

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write EPUB and apply Kindle compatibility fixes
    epub.write_epub(str(output_path), book, {})
    _scrub_epub_for_kindle(output_path)

    return output_path
