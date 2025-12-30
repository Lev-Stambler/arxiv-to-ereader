"""Tests for the converter module."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from arxiv_to_ereader.converter import convert_to_epub
from arxiv_to_ereader.parser import Figure, Paper, Section


@pytest.fixture
def sample_paper() -> Paper:
    """Create a sample Paper object for testing."""
    return Paper(
        id="2402.08954",
        title="A Sample Paper on Machine Learning",
        authors=["John Doe", "Jane Smith"],
        abstract="This is the abstract of the paper.",
        date="2024-02-15",
        sections=[
            Section(
                id="S1",
                title="Introduction",
                level=1,
                content="<p>Introduction content here.</p>",
            ),
            Section(
                id="S2",
                title="Methods",
                level=1,
                content="<p>Methods content here.</p>",
            ),
            Section(
                id="S3",
                title="Results",
                level=1,
                content="<p>Results content here.</p>",
            ),
        ],
        figures=[],
        references_html="<ul><li>[1] A reference</li></ul>",
    )


class TestConvertToEpub:
    """Tests for convert_to_epub function."""

    def test_creates_epub_file(self, sample_paper: Paper) -> None:
        """Test that an EPUB file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            assert result.exists()
            assert result.suffix == ".epub"

    def test_epub_is_valid_zip(self, sample_paper: Paper) -> None:
        """Test that the EPUB is a valid ZIP file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            # EPUB files are ZIP archives
            assert zipfile.is_zipfile(result)

    def test_epub_contains_required_files(self, sample_paper: Paper) -> None:
        """Test that the EPUB contains required structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                names = zf.namelist()

                # Must contain mimetype
                assert "mimetype" in names

                # Must contain META-INF/container.xml
                assert any("container.xml" in n for n in names)

                # Must contain content files
                assert any(".opf" in n for n in names)

    def test_epub_contains_stylesheet(self, sample_paper: Paper) -> None:
        """Test that the EPUB contains the CSS stylesheet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                names = zf.namelist()
                assert any("style.css" in n for n in names)

    def test_epub_contains_chapters(self, sample_paper: Paper) -> None:
        """Test that the EPUB contains chapter files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                names = zf.namelist()

                # Should have cover, abstract, sections, references
                xhtml_files = [n for n in names if n.endswith(".xhtml")]
                assert len(xhtml_files) >= 4  # cover + abstract + sections + refs

    def test_default_output_path(self, sample_paper: Paper) -> None:
        """Test default output path uses paper ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = convert_to_epub(sample_paper, download_images=False)
                assert result.name == "2402.08954.epub"
            finally:
                os.chdir(original_cwd)

    def test_style_presets(self, sample_paper: Paper) -> None:
        """Test different style presets produce valid EPUBs."""
        for preset in ["default", "compact", "large-text"]:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / f"test_{preset}.epub"
                result = convert_to_epub(
                    sample_paper,
                    output_path,
                    style_preset=preset,
                    download_images=False,
                )
                assert result.exists()


class TestEpubContent:
    """Tests for EPUB content correctness."""

    def test_title_in_cover(self, sample_paper: Paper) -> None:
        """Test that the title appears in the cover page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # Find cover.xhtml
                cover_files = [n for n in zf.namelist() if "cover" in n.lower()]
                assert cover_files

                cover_content = zf.read(cover_files[0]).decode("utf-8")
                assert sample_paper.title in cover_content

    def test_authors_in_cover(self, sample_paper: Paper) -> None:
        """Test that authors appear in the cover page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                cover_files = [n for n in zf.namelist() if "cover" in n.lower()]
                cover_content = zf.read(cover_files[0]).decode("utf-8")

                for author in sample_paper.authors:
                    assert author in cover_content

    def test_paper_id_in_cover(self, sample_paper: Paper) -> None:
        """Test that paper ID appears in the cover page."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                cover_files = [n for n in zf.namelist() if "cover" in n.lower()]
                cover_content = zf.read(cover_files[0]).decode("utf-8")
                assert sample_paper.id in cover_content

    def test_abstract_in_epub(self, sample_paper: Paper) -> None:
        """Test that abstract is included."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                abstract_files = [n for n in zf.namelist() if "abstract" in n.lower()]
                assert abstract_files

                abstract_content = zf.read(abstract_files[0]).decode("utf-8")
                assert sample_paper.abstract in abstract_content


class TestEpubKindleCompatibility:
    """Tests for Kindle-compatible EPUB scrubbing."""

    def test_xhtml_files_have_utf8_declaration(self, sample_paper: Paper) -> None:
        """Test that all XHTML files have proper UTF-8 encoding declaration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".xhtml"):
                        content = zf.read(name).decode("utf-8")
                        # Must have XML declaration with UTF-8 encoding
                        assert '<?xml version="1.0" encoding="utf-8"?>' in content, (
                            f"{name} missing UTF-8 encoding declaration"
                        )

    def test_opf_file_has_utf8_declaration(self, sample_paper: Paper) -> None:
        """Test that the OPF manifest has proper UTF-8 encoding declaration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".opf"):
                        content = zf.read(name).decode("utf-8")
                        assert '<?xml version="1.0" encoding="utf-8"?>' in content, (
                            "OPF file missing UTF-8 encoding declaration"
                        )

    def test_ncx_file_has_utf8_declaration(self, sample_paper: Paper) -> None:
        """Test that the NCX navigation has proper UTF-8 encoding declaration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".ncx"):
                        content = zf.read(name).decode("utf-8")
                        assert '<?xml version="1.0" encoding="utf-8"?>' in content, (
                            "NCX file missing UTF-8 encoding declaration"
                        )

    def test_mimetype_stored_uncompressed(self, sample_paper: Paper) -> None:
        """Test that mimetype is stored uncompressed (EPUB spec requirement)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                info = zf.getinfo("mimetype")
                assert info.compress_type == zipfile.ZIP_STORED, (
                    "mimetype must be stored uncompressed"
                )
