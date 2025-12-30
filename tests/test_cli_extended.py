"""Extended CLI tests with mocked HTTP."""

import tempfile
from pathlib import Path

import respx
from httpx import Response
from typer.testing import CliRunner

from arxiv_to_ereader.cli import app

runner = CliRunner()

SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Paper</title></head>
<body>
<article class="ltx_document">
    <h1 class="ltx_title ltx_title_document">Test Paper Title</h1>
    <div class="ltx_authors">
        <span class="ltx_personname">Test Author</span>
    </div>
    <div class="ltx_abstract"><p>Test abstract.</p></div>
    <section class="ltx_section" id="S1">
        <h2 class="ltx_title ltx_title_section">1 Introduction</h2>
        <div class="ltx_para"><p>Test content.</p></div>
    </section>
</article>
</body>
</html>
"""


class TestCLIConversion:
    """Tests for actual CLI conversion with mocked HTTP."""

    @respx.mock
    def test_convert_single_paper_success(self) -> None:
        """Test converting a single paper via CLI."""
        paper_id = "2402.08954"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(200, text=SAMPLE_HTML)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app, [paper_id, "-o", tmpdir, "--no-images"]
            )

            assert result.exit_code == 0
            assert "Success" in result.stdout
            assert "Test Paper Title" in result.stdout

            # Check file was created
            epub_files = list(Path(tmpdir).glob("*.epub"))
            assert len(epub_files) == 1

    @respx.mock
    def test_convert_single_paper_not_found(self) -> None:
        """Test CLI handles 404 gracefully."""
        paper_id = "0000.00000"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(404)
        )

        result = runner.invoke(app, [paper_id])

        assert result.exit_code == 1
        assert "not available" in result.stdout.lower()

    @respx.mock
    def test_convert_with_style_preset(self) -> None:
        """Test converting with different style presets."""
        paper_id = "2402.08954"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(200, text=SAMPLE_HTML)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            for style in ["default", "compact", "large-text"]:
                result = runner.invoke(
                    app,
                    [paper_id, "-o", tmpdir, "--style", style, "--no-images"],
                )
                # Each should succeed (may overwrite same file)
                assert result.exit_code == 0

    @respx.mock
    def test_convert_from_url(self) -> None:
        """Test converting from arXiv URL."""
        paper_id = "2402.08954"
        url = f"https://arxiv.org/abs/{paper_id}"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(200, text=SAMPLE_HTML)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, [url, "-o", tmpdir, "--no-images"])

            assert result.exit_code == 0
            assert "Success" in result.stdout


class TestCLIBatchConversion:
    """Tests for batch conversion via CLI."""

    @respx.mock
    def test_batch_convert_multiple_papers(self) -> None:
        """Test converting multiple papers via CLI."""
        papers = ["2402.08954", "1234.56789"]

        for paper_id in papers:
            respx.get(f"https://arxiv.org/html/{paper_id}").mock(
                return_value=Response(200, text=SAMPLE_HTML)
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use --use-id to ensure unique filenames since sample HTML has same title
            result = runner.invoke(
                app, [*papers, "-o", tmpdir, "--no-images", "--use-id"]
            )

            assert result.exit_code == 0
            assert "2 succeeded" in result.stdout

            # Check files were created with arXiv IDs
            epub_files = list(Path(tmpdir).glob("*.epub"))
            assert len(epub_files) == 2

    @respx.mock
    def test_batch_convert_partial_failure(self) -> None:
        """Test batch conversion with some failures."""
        respx.get("https://arxiv.org/html/2402.08954").mock(
            return_value=Response(200, text=SAMPLE_HTML)
        )
        respx.get("https://arxiv.org/html/0000.00000").mock(
            return_value=Response(404)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(
                app,
                ["2402.08954", "0000.00000", "-o", tmpdir, "--no-images"],
            )

            assert result.exit_code == 0
            assert "1 succeeded" in result.stdout
            assert "1 failed" in result.stdout
