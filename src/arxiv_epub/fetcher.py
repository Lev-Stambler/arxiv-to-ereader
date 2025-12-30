"""Fetch arXiv HTML papers."""

import re
from urllib.parse import urlparse

import httpx

# Pattern to match arXiv IDs: YYMM.NNNNN or old format like hep-th/9901001
ARXIV_ID_PATTERN = re.compile(
    r"(?:arxiv:)?(?:abs/|html/|pdf/)?"
    r"((?:\d{4}\.\d{4,5}(?:v\d+)?)|(?:[a-z-]+/\d{7}(?:v\d+)?))",
    re.IGNORECASE,
)


class ArxivFetchError(Exception):
    """Error fetching arXiv paper."""

    pass


class ArxivHTMLNotAvailable(ArxivFetchError):
    """HTML version not available for this paper."""

    pass


def normalize_arxiv_id(input_str: str) -> str:
    """Extract and normalize arXiv ID from URL or ID string.

    Args:
        input_str: arXiv URL or ID (e.g., "2402.08954", "https://arxiv.org/abs/2402.08954")

    Returns:
        Normalized arXiv ID (e.g., "2402.08954")

    Raises:
        ValueError: If no valid arXiv ID can be extracted
    """
    input_str = input_str.strip()

    # Try to parse as URL first
    parsed = urlparse(input_str)
    if parsed.scheme:
        # It's a URL, extract path
        path = parsed.path
        match = ARXIV_ID_PATTERN.search(path)
        if match:
            return match.group(1)
    else:
        # Try direct match
        match = ARXIV_ID_PATTERN.search(input_str)
        if match:
            return match.group(1)

    raise ValueError(f"Could not extract arXiv ID from: {input_str}")


def get_html_url(paper_id: str) -> str:
    """Get the HTML URL for an arXiv paper.

    Args:
        paper_id: Normalized arXiv paper ID

    Returns:
        URL to the HTML version of the paper
    """
    return f"https://arxiv.org/html/{paper_id}"


def get_abs_url(paper_id: str) -> str:
    """Get the abstract page URL for an arXiv paper.

    Args:
        paper_id: Normalized arXiv paper ID

    Returns:
        URL to the abstract page
    """
    return f"https://arxiv.org/abs/{paper_id}"


def fetch_paper(paper_id_or_url: str, timeout: float = 30.0) -> tuple[str, str]:
    """Fetch the HTML content of an arXiv paper.

    Args:
        paper_id_or_url: arXiv paper ID or URL
        timeout: Request timeout in seconds

    Returns:
        Tuple of (paper_id, html_content)

    Raises:
        ArxivHTMLNotAvailable: If HTML version is not available
        ArxivFetchError: For other fetch errors
    """
    paper_id = normalize_arxiv_id(paper_id_or_url)
    url = get_html_url(paper_id)

    headers = {
        "User-Agent": "arxiv-epub/0.1.0 (https://github.com/Lev-Stambler/arxiv-epub)",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers=headers)

            if response.status_code == 404:
                raise ArxivHTMLNotAvailable(
                    f"HTML version not available for paper {paper_id}. "
                    "This paper may predate HTML support (Dec 2023) or failed conversion."
                )

            response.raise_for_status()
            return paper_id, response.text

    except httpx.TimeoutException as e:
        raise ArxivFetchError(f"Timeout fetching paper {paper_id}: {e}") from e
    except httpx.HTTPStatusError as e:
        raise ArxivFetchError(f"HTTP error fetching paper {paper_id}: {e}") from e
    except httpx.RequestError as e:
        raise ArxivFetchError(f"Error fetching paper {paper_id}: {e}") from e


async def fetch_paper_async(paper_id_or_url: str, timeout: float = 30.0) -> tuple[str, str]:
    """Async version of fetch_paper.

    Args:
        paper_id_or_url: arXiv paper ID or URL
        timeout: Request timeout in seconds

    Returns:
        Tuple of (paper_id, html_content)
    """
    paper_id = normalize_arxiv_id(paper_id_or_url)
    url = get_html_url(paper_id)

    headers = {
        "User-Agent": "arxiv-epub/0.1.0 (https://github.com/Lev-Stambler/arxiv-epub)",
        "Accept": "text/html,application/xhtml+xml",
    }

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)

        if response.status_code == 404:
            raise ArxivHTMLNotAvailable(
                f"HTML version not available for paper {paper_id}. "
                "This paper may predate HTML support (Dec 2023) or failed conversion."
            )

        response.raise_for_status()
        return paper_id, response.text


async def fetch_papers_batch(
    paper_ids: list[str], timeout: float = 30.0
) -> list[tuple[str, str | Exception]]:
    """Fetch multiple papers concurrently.

    Args:
        paper_ids: List of paper IDs or URLs
        timeout: Request timeout in seconds

    Returns:
        List of tuples (paper_id, html_content or Exception)
    """
    import asyncio

    async def fetch_one(paper_id: str) -> tuple[str, str | Exception]:
        try:
            return await fetch_paper_async(paper_id, timeout)
        except Exception as e:
            return normalize_arxiv_id(paper_id), e

    return await asyncio.gather(*[fetch_one(pid) for pid in paper_ids])
