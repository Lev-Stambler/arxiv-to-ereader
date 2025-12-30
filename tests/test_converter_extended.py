"""Extended converter tests."""

import tempfile
import zipfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from arxiv_to_ereader.converter import (
    _convert_math_to_images,
    _download_image,
    convert_to_epub,
)
from arxiv_to_ereader.parser import Figure, Footnote, Paper, Section


class TestImageDownload:
    """Tests for image download functionality."""

    @respx.mock
    def test_download_image_success(self) -> None:
        """Test successful image download."""
        image_url = "https://arxiv.org/html/1234.56789/figure1.png"
        image_content = b"\x89PNG\r\n\x1a\n fake png data"

        respx.get(image_url).mock(
            return_value=Response(
                200,
                content=image_content,
                headers={"content-type": "image/png"},
            )
        )

        result = _download_image(image_url)
        assert result is not None
        data, media_type = result
        assert data == image_content
        assert media_type == "image/png"

    @respx.mock
    def test_download_image_jpeg(self) -> None:
        """Test downloading JPEG image."""
        image_url = "https://arxiv.org/html/1234.56789/figure1.jpg"
        image_content = b"\xff\xd8\xff fake jpeg"

        respx.get(image_url).mock(
            return_value=Response(
                200,
                content=image_content,
                headers={"content-type": "image/jpeg; charset=utf-8"},
            )
        )

        result = _download_image(image_url)
        assert result is not None
        _, media_type = result
        assert media_type == "image/jpeg"

    @respx.mock
    def test_download_image_failure(self) -> None:
        """Test failed image download returns None."""
        image_url = "https://arxiv.org/html/1234.56789/missing.png"

        respx.get(image_url).mock(return_value=Response(404))

        result = _download_image(image_url)
        assert result is None

    @respx.mock
    def test_download_image_timeout(self) -> None:
        """Test image download timeout returns None."""
        import httpx

        image_url = "https://arxiv.org/html/1234.56789/slow.png"

        respx.get(image_url).mock(side_effect=httpx.TimeoutException("timeout"))

        result = _download_image(image_url)
        assert result is None


class TestConverterWithImages:
    """Tests for converter with image handling."""

    @respx.mock
    def test_convert_with_images(self) -> None:
        """Test conversion with image downloading."""
        image_url = "https://arxiv.org/html/test/figure1.png"
        image_content = b"\x89PNG\r\n\x1a\n fake png"

        respx.get(image_url).mock(
            return_value=Response(
                200,
                content=image_content,
                headers={"content-type": "image/png"},
            )
        )

        paper = Paper(
            id="test.00001",
            title="Test Paper with Images",
            authors=["Author"],
            abstract="Abstract",
            sections=[
                Section(
                    id="S1",
                    title="Results",
                    level=1,
                    content=f'<p>See figure: <img src="{image_url}"/></p>',
                )
            ],
            figures=[
                Figure(
                    id="fig1",
                    caption="Test figure",
                    image_url=image_url,
                )
            ],
            all_images={image_url: image_url},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=True)

            assert result.exists()

            # Check image is in EPUB
            import zipfile

            with zipfile.ZipFile(result, "r") as zf:
                image_files = [n for n in zf.namelist() if "images/" in n]
                assert len(image_files) == 1

    @respx.mock
    def test_convert_with_missing_images(self) -> None:
        """Test conversion continues when images fail to download."""
        image_url = "https://arxiv.org/html/test/missing.png"

        respx.get(image_url).mock(return_value=Response(404))

        paper = Paper(
            id="test.00001",
            title="Test Paper",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
            figures=[
                Figure(
                    id="fig1",
                    caption="Missing figure",
                    image_url=image_url,
                )
            ],
            all_images={image_url: image_url},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            # Should not raise, just skip the image
            result = convert_to_epub(paper, output_path, download_images=True)
            assert result.exists()


class TestConverterEdgeCases:
    """Edge case tests for the converter."""

    def test_convert_paper_without_abstract(self) -> None:
        """Test converting paper with no abstract."""
        paper = Paper(
            id="test.00001",
            title="Paper Without Abstract",
            authors=["Author"],
            abstract="",  # Empty abstract
            sections=[
                Section(id="S1", title="Content", level=1, content="<p>Text</p>")
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_without_sections(self) -> None:
        """Test converting paper with no sections."""
        paper = Paper(
            id="test.00001",
            title="Paper Without Sections",
            authors=["Author"],
            abstract="Just an abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_without_references(self) -> None:
        """Test converting paper with no references."""
        paper = Paper(
            id="test.00001",
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
            references_html=None,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_without_date(self) -> None:
        """Test converting paper with no date."""
        paper = Paper(
            id="test.00001",
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            date=None,
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_with_old_format_id(self) -> None:
        """Test converting paper with old-format arXiv ID."""
        paper = Paper(
            id="hep-th/9901001",
            title="Old Format Paper",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Don't specify output path to test default naming
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = convert_to_epub(paper, download_images=False)
                assert result.exists()
                # Filename should have slash replaced
                assert "hep-th_9901001" in result.name
            finally:
                os.chdir(original_cwd)


class TestMathConversion:
    """Tests for math-to-image conversion in converter."""

    def test_convert_math_to_images_inline(self) -> None:
        """Test that inline math IS converted to images with vertical-align style."""
        html = '<p>The formula <math alttext="x + y" display="inline"><mi>x</mi></math> is simple.</p>'
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        # Inline math should be converted to images
        assert len(math_images) == 1
        # Should have img tag with math-inline class
        assert '<img' in result
        assert 'class="math-image math-inline"' in result
        # Should have vertical-align style for baseline alignment
        assert 'style=' in result
        assert 'vertical-align:' in result

    def test_convert_math_inline_vertical_align_format(self) -> None:
        """Test that vertical-align style has correct CSS format."""
        html = '<p><math alttext="x_i" display="inline"><mi>x</mi></math></p>'
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        # Check vertical-align has em units
        import re
        match = re.search(r'vertical-align:\s*(-?[\d.]+)em', result)
        assert match is not None, f"vertical-align not found in: {result}"
        depth_value = float(match.group(1))
        # Should be a reasonable value (negative for below baseline)
        assert -2.0 < depth_value < 0.5

    def test_convert_math_display_no_vertical_align(self) -> None:
        """Test that display math does NOT have vertical-align style."""
        html = '<div><math alttext="E = mc^2" display="block"><mi>E</mi></math></div>'
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        # Display math should be in a wrapper div, not have vertical-align
        assert 'class="math-block-img"' in result
        assert 'class="math-image math-display"' in result
        # The display img should NOT have inline vertical-align style
        # (it's centered in a block div instead)
        import re
        display_img = re.search(r'<img[^>]*class="math-image math-display"[^>]*>', result)
        assert display_img is not None
        assert 'vertical-align:' not in display_img.group(0)

    def test_convert_math_inline_subscript_has_depth(self) -> None:
        """Test that subscripts have appropriate vertical alignment."""
        html = '<p><math alttext="x_i" display="inline"><mi>x</mi></math></p>'
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        # Subscripts should have negative vertical-align (below baseline)
        import re
        match = re.search(r'vertical-align:\s*(-?[\d.]+)em', result)
        assert match is not None
        depth_value = float(match.group(1))
        # Subscripts extend below baseline, should be negative
        assert depth_value < 0

    def test_convert_math_to_images_display(self) -> None:
        """Test converting display math to images."""
        html = '<div><math alttext="E = mc^2" display="block"><mi>E</mi></math></div>'
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        assert len(math_images) == 1
        assert '<div class="math-block-img">' in result
        assert 'class="math-image math-display"' in result

    def test_convert_math_deduplicates(self) -> None:
        """Test that same display math expressions share the same image."""
        html = '''
        <div><math alttext="x" display="block"><mi>x</mi></math></div>
        <div><math alttext="x" display="block"><mi>x</mi></math></div>
        '''
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        # Should only have one image despite two math elements
        assert len(math_images) == 1
        # But result should have two img tags
        assert result.count('<img') == 2

    def test_convert_math_extracts_from_annotation(self) -> None:
        """Test extracting LaTeX from annotation element (display math only)."""
        html = '''
        <math display="block">
            <semantics>
                <mi>y</mi>
                <annotation encoding="application/x-tex">y^2</annotation>
            </semantics>
        </math>
        '''
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        assert len(math_images) == 1
        assert "y^2" in math_images

    def test_convert_math_preserves_non_math_content(self) -> None:
        """Test that non-math content is preserved."""
        html = '<p>Regular text here.</p><p>More text.</p>'
        math_images: dict = {}

        result, math_images = _convert_math_to_images(html, math_images)

        assert len(math_images) == 0
        assert 'Regular text here.' in result
        assert 'More text.' in result

    def test_epub_with_math_rendering_enabled(self) -> None:
        """Test full EPUB conversion with math rendering (display math only)."""
        paper = Paper(
            id="test.00001",
            title="Math Paper",
            authors=["Author"],
            abstract="A paper about math",
            sections=[
                Section(
                    id="S1",
                    title="Introduction",
                    level=1,
                    content='<div><math alttext="\\alpha + \\beta" display="block"><mi>α</mi></math></div>',
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "math_test.epub"
            result = convert_to_epub(
                paper,
                output_path,
                download_images=False,
                render_math=True,
                math_dpi=100,
            )

            assert result.exists()

            # Check that math images are in the EPUB
            with zipfile.ZipFile(result, "r") as zf:
                math_files = [n for n in zf.namelist() if "math/" in n]
                assert len(math_files) >= 1

    def test_epub_with_math_rendering_disabled(self) -> None:
        """Test EPUB conversion with math rendering disabled."""
        paper = Paper(
            id="test.00001",
            title="Math Paper",
            authors=["Author"],
            abstract="A paper about math",
            sections=[
                Section(
                    id="S1",
                    title="Introduction",
                    level=1,
                    content='<p>Consider <math alttext="x"><mi>x</mi></math>.</p>',
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "no_math_test.epub"
            result = convert_to_epub(
                paper,
                output_path,
                download_images=False,
                render_math=False,
            )

            assert result.exists()

            # Math images should NOT be in the EPUB
            with zipfile.ZipFile(result, "r") as zf:
                math_files = [n for n in zf.namelist() if "math/" in n]
                assert len(math_files) == 0


class TestFootnotesConversion:
    """Tests for footnotes in converter."""

    def test_epub_with_footnotes(self) -> None:
        """Test EPUB generation with footnotes."""
        paper = Paper(
            id="test.00001",
            title="Paper with Footnotes",
            authors=["Author"],
            abstract="Abstract",
            sections=[
                Section(
                    id="S1",
                    title="Content",
                    level=1,
                    content='<p>Text with note.<a href="#fn-1" id="fnref-1" class="footnote-ref"><sup>1</sup></a></p>',
                )
            ],
            footnotes=[
                Footnote(id="fn-1", index=1, content="This is a footnote.")
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "footnotes_test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            assert result.exists()

            # Check footnotes chapter exists
            with zipfile.ZipFile(result, "r") as zf:
                assert "EPUB/footnotes.xhtml" in zf.namelist()
                footnotes_content = zf.read("EPUB/footnotes.xhtml").decode("utf-8")
                assert "This is a footnote." in footnotes_content
