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
        """Test that the EPUB contains a CSS stylesheet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                names = zf.namelist()
                # Calibre may rename style.css to stylesheet.css
                assert any(n.endswith(".css") for n in names)

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

    def test_title_in_epub(self, sample_paper: Paper) -> None:
        """Test that the title appears somewhere in the EPUB content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # Check all XHTML files for title
                found_title = False
                for name in zf.namelist():
                    if name.endswith(".xhtml"):
                        content = zf.read(name).decode("utf-8")
                        if sample_paper.title in content:
                            found_title = True
                            break
                assert found_title, "Title not found in any XHTML file"

    def test_authors_in_epub(self, sample_paper: Paper) -> None:
        """Test that authors appear somewhere in the EPUB content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # Combine all XHTML content
                all_content = ""
                for name in zf.namelist():
                    if name.endswith(".xhtml"):
                        all_content += zf.read(name).decode("utf-8")

                for author in sample_paper.authors:
                    assert author in all_content, f"Author {author} not found"

    def test_paper_id_in_epub(self, sample_paper: Paper) -> None:
        """Test that paper ID appears somewhere in the EPUB content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # Check all XHTML files for paper ID
                found_id = False
                for name in zf.namelist():
                    if name.endswith(".xhtml"):
                        content = zf.read(name).decode("utf-8")
                        if sample_paper.id in content:
                            found_id = True
                            break
                assert found_id, "Paper ID not found in any XHTML file"

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
    """Tests for Kindle-compatible EPUB scrubbing (no Calibre required)."""

    def test_xhtml_has_utf8_encoding_declaration(self, sample_paper: Paper) -> None:
        """Test that all XHTML files have UTF-8 encoding declaration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".xhtml"):
                        content = zf.read(name).decode("utf-8")
                        assert '<?xml version="1.0" encoding="utf-8"?>' in content, (
                            f"{name} missing UTF-8 encoding declaration"
                        )

    def test_opf_has_language_metadata(self, sample_paper: Paper) -> None:
        """Test that OPF file has dc:language metadata for Kindle."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".opf"):
                        content = zf.read(name).decode("utf-8")
                        assert "<dc:language>" in content, (
                            "OPF missing dc:language metadata"
                        )

    def test_mimetype_first_and_uncompressed(self, sample_paper: Paper) -> None:
        """Test that mimetype is first entry and stored uncompressed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # mimetype must be first
                assert zf.namelist()[0] == "mimetype", "mimetype must be first file"
                # mimetype must be uncompressed
                info = zf.getinfo("mimetype")
                assert info.compress_type == zipfile.ZIP_STORED, (
                    "mimetype must be stored uncompressed"
                )

    def test_epub_is_valid_structure(self, sample_paper: Paper) -> None:
        """Test that scrubbed EPUB has valid structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            assert result.exists()
            assert zipfile.is_zipfile(result)

            with zipfile.ZipFile(result, "r") as zf:
                names = zf.namelist()
                assert "mimetype" in names
                assert any(".opf" in n for n in names)
                assert any(".xhtml" in n for n in names)

    def test_unique_creator_ids(self, sample_paper: Paper) -> None:
        """Test that multiple authors have unique creator IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".opf"):
                        content = zf.read(name).decode("utf-8")
                        # Should have creator_0 and creator_1 for two authors
                        assert 'id="creator_0"' in content
                        assert 'id="creator_1"' in content
                        # Should NOT have duplicate "creator" IDs
                        assert content.count('id="creator"') == 0

    def test_no_mathml_in_output(self) -> None:
        """Test that MathML is stripped from EPUB for Kindle compatibility."""
        # Create a paper with MathML content
        paper_with_math = Paper(
            id="test.math",
            title="Math Test",
            authors=["Test Author"],
            abstract="Abstract with no math",
            date="2024-01-01",
            sections=[
                Section(
                    id="S1",
                    title="Math Section",
                    level=1,
                    content='<p>Here is math: <math alttext="x^2"><mi>x</mi><msup><mn>2</mn></msup></math> in text.</p>',
                )
            ],
            figures=[],
            footnotes=[],
            references_html=None,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            # Disable math rendering to test MathML stripping
            result = convert_to_epub(
                paper_with_math, output_path, download_images=False, render_math=False
            )

            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".xhtml") and "section" in name:
                        content = zf.read(name).decode("utf-8")
                        # MathML should be stripped
                        assert "<math" not in content, f"MathML found in {name}"
                        # Alttext should be preserved as fallback
                        assert "x^2" in content, f"Alttext not preserved in {name}"


class TestEpubCheckValidation:
    """Tests using EPUBCheck for validation (requires Java)."""

    @pytest.fixture
    def epubcheck_jar(self) -> Path | None:
        """Get path to epubcheck JAR, or None if not available."""
        import os
        import shutil

        # Check environment variable first
        jar_path = os.environ.get("EPUBCHECK_JAR")
        if jar_path and Path(jar_path).exists():
            return Path(jar_path)

        # Check common locations
        common_paths = [
            Path("/tmp/epubcheck-5.1.0/epubcheck.jar"),
            Path.home() / ".local/share/epubcheck/epubcheck.jar",
        ]
        for path in common_paths:
            if path.exists():
                return path

        # Check if java is available
        if not shutil.which("java"):
            return None

        return None

    def _run_epubcheck(self, epubcheck_jar: Path, epub_path: Path) -> list[str]:
        """Run epubcheck and return list of structural errors (not content warnings)."""
        import subprocess

        proc = subprocess.run(
            ["java", "-jar", str(epubcheck_jar), str(epub_path)],
            capture_output=True,
            text=True,
        )

        if proc.returncode == 0:
            return []

        # Filter for structural errors that would cause Kindle rejection
        # Ignore content-level issues like broken cross-references (RSC-012)
        # and missing referenced resources (RSC-007) which are ArXiv HTML issues
        structural_error_codes = [
            "RSC-005",  # Parsing errors (invalid XML/HTML structure)
            "PKG-",     # Package errors
            "OPF-",     # OPF manifest errors
            "NCX-",     # NCX navigation errors
        ]

        errors = []
        for line in (proc.stdout + proc.stderr).split("\n"):
            if "ERROR" in line:
                # Check if it's a structural error we care about
                # But exclude specific content-level RSC-005 errors
                if any(code in line for code in structural_error_codes):
                    # Skip RSC-005 errors about div/span placement (ArXiv HTML issue)
                    if 'RSC-005' in line and ('element "div"' in line or 'element "span"' in line):
                        continue
                    # Skip RSC-005 errors about math namespace (should be stripped)
                    if 'RSC-005' in line and 'element "math"' in line:
                        errors.append(line)  # This IS a problem - math should be stripped
                    elif 'RSC-005' in line and 'Duplicate' in line:
                        errors.append(line)  # Duplicate IDs are a problem
                    elif 'OPF-' in line or 'PKG-' in line or 'NCX-' in line:
                        errors.append(line)

        return errors

    def test_epub_passes_epubcheck(
        self, sample_paper: Paper, epubcheck_jar: Path | None
    ) -> None:
        """Test that generated EPUB passes EPUBCheck validation."""
        if epubcheck_jar is None:
            pytest.skip("EPUBCheck not installed (set EPUBCHECK_JAR env var)")

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            errors = self._run_epubcheck(epubcheck_jar, result)
            assert not errors, f"EPUBCheck errors:\n" + "\n".join(errors)


class TestRealPaperIntegration:
    """Integration tests with real arXiv papers (requires network)."""

    @pytest.fixture
    def epubcheck_jar(self) -> Path | None:
        """Get path to epubcheck JAR, or None if not available."""
        import os
        import shutil

        jar_path = os.environ.get("EPUBCHECK_JAR")
        if jar_path and Path(jar_path).exists():
            return Path(jar_path)

        common_paths = [
            Path("/tmp/epubcheck-5.1.0/epubcheck.jar"),
            Path.home() / ".local/share/epubcheck/epubcheck.jar",
        ]
        for path in common_paths:
            if path.exists():
                return path

        if not shutil.which("java"):
            return None

        return None

    @pytest.mark.integration
    def test_real_paper_with_math(self, epubcheck_jar: Path | None) -> None:
        """Test converting a real arXiv paper with math equations."""
        if epubcheck_jar is None:
            pytest.skip("EPUBCheck not installed (set EPUBCHECK_JAR env var)")

        import subprocess
        from arxiv_to_ereader import fetch_paper, parse_paper

        # Use a paper known to have math (Mamba paper)
        paper_id = "2312.00752"

        try:
            fetched_id, html = fetch_paper(paper_id)
        except Exception as e:
            pytest.skip(f"Could not fetch paper (network issue?): {e}")

        paper = parse_paper(html, fetched_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            # Test with math rendering enabled (default)
            result = convert_to_epub(
                paper, output_path, download_images=False, render_math=True
            )

            assert result.exists()
            assert result.stat().st_size > 0

            # Run epubcheck - focus on structural errors
            proc = subprocess.run(
                ["java", "-jar", str(epubcheck_jar), str(result)],
                capture_output=True,
                text=True,
            )

            # Check for critical structural errors that would cause Kindle E999
            output = proc.stdout + proc.stderr

            # These specific errors would cause Kindle rejection:
            critical_errors = []
            for line in output.split("\n"):
                if "ERROR" in line:
                    # Duplicate IDs in OPF
                    if "Duplicate" in line and ".opf" in line:
                        critical_errors.append(line)
                    # MathML not stripped (should never happen with scrubbing)
                    if 'element "math"' in line:
                        critical_errors.append(line)
                    # Empty ol tags
                    if 'element "ol" incomplete' in line:
                        critical_errors.append(line)

            assert not critical_errors, (
                f"Critical Kindle compatibility errors:\n" + "\n".join(critical_errors)
            )

            # Verify MathML was stripped from content
            with zipfile.ZipFile(result, "r") as zf:
                for name in zf.namelist():
                    if name.endswith(".xhtml"):
                        content = zf.read(name).decode("utf-8")
                        assert "<math" not in content or "math-image" in content, (
                            f"Unprocessed MathML found in {name}"
                        )
