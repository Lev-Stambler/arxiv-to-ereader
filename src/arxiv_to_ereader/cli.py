"""Command-line interface for arxiv-to-ereader."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from arxiv_to_ereader import __version__
from arxiv_to_ereader.converter import OutputFormat, convert_to_epub
from arxiv_to_ereader.fetcher import (
    ArxivFetchError,
    ArxivHTMLNotAvailable,
    fetch_paper,
    fetch_papers_batch,
    normalize_arxiv_id,
)
from arxiv_to_ereader.parser import parse_paper

app = typer.Typer(
    name="arxiv-to-ereader",
    help="Convert arXiv HTML papers to EPUB and Kindle formats.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"arxiv-to-ereader version {__version__}")
        raise typer.Exit()


@app.command()
def convert(
    papers: Annotated[
        list[str],
        typer.Argument(
            help="arXiv paper IDs or URLs (e.g., 2402.08954 or https://arxiv.org/abs/2402.08954)"
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for ebook files",
        ),
    ] = None,
    format: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Output format: epub, mobi, or azw3 (Kindle)",
        ),
    ] = "epub",
    style: Annotated[
        str,
        typer.Option(
            "--style",
            "-s",
            help="Style preset: default, compact, or large-text",
        ),
    ] = "default",
    no_images: Annotated[
        bool,
        typer.Option(
            "--no-images",
            help="Skip downloading images (faster, smaller files)",
        ),
    ] = False,
    no_math_images: Annotated[
        bool,
        typer.Option(
            "--no-math-images",
            help="Don't render math equations as images (keep MathML, may not display on Kindle)",
        ),
    ] = False,
    math_dpi: Annotated[
        int,
        typer.Option(
            "--math-dpi",
            help="DPI resolution for rendered math images (default 150)",
        ),
    ] = 150,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """Convert arXiv papers to EPUB or Kindle format.

    Examples:

        arxiv-to-ereader 2402.08954

        arxiv-to-ereader 2402.08954 --format azw3

        arxiv-to-ereader 2402.08954 2401.12345 -o ~/kindle/ -f mobi

        arxiv-to-ereader https://arxiv.org/abs/2402.08954 --style large-text
    """
    if style not in ("default", "compact", "large-text"):
        console.print(f"[red]Error:[/red] Invalid style '{style}'. Use default, compact, or large-text.")
        raise typer.Exit(1)

    # Validate format
    try:
        output_format = OutputFormat(format.lower())
    except ValueError:
        console.print(f"[red]Error:[/red] Invalid format '{format}'. Use epub, mobi, or azw3.")
        raise typer.Exit(1)

    # Create output directory if specified
    if output:
        output.mkdir(parents=True, exist_ok=True)

    # Process single paper or batch
    if len(papers) == 1:
        _convert_single(papers[0], output, style, not no_images, output_format, not no_math_images, math_dpi)
    else:
        _convert_batch(papers, output, style, not no_images, output_format, not no_math_images, math_dpi)


def _convert_single(
    paper_input: str,
    output_dir: Path | None,
    style: str,
    download_images: bool,
    output_format: OutputFormat,
    render_math: bool,
    math_dpi: int,
) -> None:
    """Convert a single paper."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Normalize ID
        try:
            paper_id = normalize_arxiv_id(paper_input)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        task = progress.add_task(f"Fetching {paper_id}...", total=None)

        # Fetch HTML
        try:
            _, html = fetch_paper(paper_input)
        except ArxivHTMLNotAvailable as e:
            progress.stop()
            console.print(f"[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1)
        except ArxivFetchError as e:
            progress.stop()
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, description=f"Parsing {paper_id}...")

        # Parse HTML
        paper = parse_paper(html, paper_id)

        format_name = output_format.value.upper()
        progress.update(task, description=f"Converting {paper_id} to {format_name}...")

        # Determine output path
        if output_dir:
            output_path = output_dir / f"{paper_id.replace('/', '_')}.{output_format.value}"
        else:
            output_path = None

        # Convert to ebook
        ebook_path = convert_to_epub(
            paper,
            output_path=output_path,
            style_preset=style,
            download_images=download_images,
            output_format=output_format,
            render_math=render_math,
            math_dpi=math_dpi,
        )

        progress.stop()

    console.print(f"[green]Success![/green] Created: {ebook_path}")
    console.print(f"  Title: {paper.title}")
    console.print(f"  Authors: {', '.join(paper.authors)}")


def _convert_batch(
    paper_inputs: list[str],
    output_dir: Path | None,
    style: str,
    download_images: bool,
    output_format: OutputFormat,
    render_math: bool,
    math_dpi: int,
) -> None:
    """Convert multiple papers."""
    format_name = output_format.value.upper()
    console.print(f"Converting {len(paper_inputs)} papers to {format_name}...")

    # Fetch all papers concurrently
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching papers...", total=None)
        results = asyncio.run(fetch_papers_batch(paper_inputs))
        progress.stop()

    # Process results
    success_count = 0
    error_count = 0

    for paper_id, result in results:
        if isinstance(result, Exception):
            console.print(f"[red]Error[/red] {paper_id}: {result}")
            error_count += 1
            continue

        html = result
        console.print(f"[dim]Processing {paper_id}...[/dim]")

        try:
            # Parse HTML
            paper = parse_paper(html, paper_id)

            # Determine output path
            if output_dir:
                output_path = output_dir / f"{paper_id.replace('/', '_')}.{output_format.value}"
            else:
                output_path = None

            # Convert to ebook
            ebook_path = convert_to_epub(
                paper,
                output_path=output_path,
                style_preset=style,
                download_images=download_images,
                output_format=output_format,
                render_math=render_math,
                math_dpi=math_dpi,
            )

            console.print(f"[green]Created:[/green] {ebook_path}")
            success_count += 1

        except Exception as e:
            console.print(f"[red]Error[/red] converting {paper_id}: {e}")
            error_count += 1

    # Summary
    console.print()
    console.print(f"[bold]Summary:[/bold] {success_count} succeeded, {error_count} failed")


if __name__ == "__main__":
    app()
