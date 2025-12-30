"""Convert LaTeX math equations to images for e-reader compatibility."""

import hashlib
import io
import re
from dataclasses import dataclass

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.mathtext import MathTextParser, math_to_image

# Use non-interactive backend for headless rendering
matplotlib.use("Agg")


@dataclass
class MathImage:
    """A rendered math equation as an image."""

    latex: str
    image_data: bytes
    image_type: str = "image/png"
    is_display: bool = False  # True for block/display equations, False for inline
    depth_em: float = 0.0  # Vertical offset in em (negative = below baseline)

    @property
    def filename(self) -> str:
        """Generate a unique filename based on the LaTeX content."""
        hash_val = hashlib.md5(self.latex.encode()).hexdigest()[:12]
        return f"math_{hash_val}.png"


def _clean_latex(latex: str) -> str:
    """Clean LaTeX string for matplotlib rendering.

    Matplotlib's mathtext doesn't support all LaTeX commands.
    This function converts/removes unsupported commands.
    """
    # Remove leading/trailing whitespace
    latex = latex.strip()

    # Common substitutions for unsupported commands
    substitutions = [
        # Text commands - convert to regular text
        (r"\\text\{([^}]*)\}", r"\\mathrm{\1}"),
        (r"\\textbf\{([^}]*)\}", r"\\mathbf{\1}"),
        (r"\\textit\{([^}]*)\}", r"\\mathit{\1}"),
        (r"\\textrm\{([^}]*)\}", r"\\mathrm{\1}"),
        # Spacing commands
        (r"\\,", " "),
        (r"\\;", " "),
        (r"\\:", " "),
        (r"\\!", ""),
        (r"\\quad", "  "),
        (r"\\qquad", "    "),
        # Common unsupported commands -> supported equivalents
        (r"\\left\[", "["),
        (r"\\right\]", "]"),
        (r"\\left\(", "("),
        (r"\\right\)", ")"),
        (r"\\left\{", r"\\{"),
        (r"\\right\}", r"\\}"),
        (r"\\left\|", "|"),
        (r"\\right\|", "|"),
        (r"\\left\\langle", r"\\langle"),
        (r"\\right\\rangle", r"\\rangle"),
        (r"\\left\.", ""),
        (r"\\right\.", ""),
        # Operators
        (r"\\operatorname\{([^}]*)\}", r"\\mathrm{\1}"),
        (r"\\mathop\{([^}]*)\}", r"\\mathrm{\1}"),
        # Remove unsupported sizing
        (r"\\big", ""),
        (r"\\Big", ""),
        (r"\\bigg", ""),
        (r"\\Bigg", ""),
        # Handle \setminus (set minus) - not in mathtext
        (r"\\setminus", r"\\backslash"),
        # Handle \mid (conditional probability separator)
        (r"\\mid", "|"),
        # Remove intent attribute artifacts if present
        (r":literal", ""),
    ]

    for pattern, replacement in substitutions:
        latex = re.sub(pattern, replacement, latex)

    return latex


def _simple_latex_fallback(latex: str) -> str:
    """Create a very simple representation for complex LaTeX."""
    # Remove all commands and just keep basic content
    simple = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", latex)
    simple = re.sub(r"\\[a-zA-Z]+", "", simple)
    simple = re.sub(r"[_^]", "", simple)
    simple = re.sub(r"[{}]", "", simple)
    return simple.strip() or "?"


def render_latex_to_image(
    latex: str,
    dpi: int = 200,
    is_display: bool = False,
) -> MathImage | None:
    """Render a LaTeX equation to a PNG image with white background.

    Uses matplotlib's mathtext engine which doesn't require a LaTeX installation.
    Renders with a white background for better Kindle compatibility.

    Args:
        latex: LaTeX math expression (without $ delimiters)
        dpi: Resolution for the output image (default 200 for crisp rendering)
        is_display: Whether this is a display/block equation

    Returns:
        MathImage with the rendered equation, or None if rendering fails
    """
    if not latex or not latex.strip():
        return None

    # Clean the LaTeX for matplotlib
    cleaned = _clean_latex(latex)

    # Wrap in $ for mathtext
    if not cleaned.startswith("$"):
        cleaned = f"${cleaned}$"

    depth_em = 0.0  # Default depth

    try:
        # Create figure and render math
        fig, ax = plt.subplots(figsize=(0.01, 0.01))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")
        ax.axis("off")

        # Render the math text
        try:
            text = ax.text(
                0.5, 0.5, cleaned,
                fontsize=12,
                ha="center", va="center",
                transform=ax.transAxes,
            )
        except ValueError:
            # If mathtext fails, try with simplified LaTeX
            simple = _simple_latex_fallback(latex)
            if simple:
                text = ax.text(
                    0.5, 0.5, f"${simple}$",
                    fontsize=12,
                    ha="center", va="center",
                    transform=ax.transAxes,
                )
                cleaned = f"${simple}$"  # Update for depth calculation
            else:
                plt.close(fig)
                return None

        # Render to get bounding box
        fig.canvas.draw()

        # Get tight bounding box around text
        bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())
        bbox = bbox.expanded(1.1, 1.2)  # Add padding

        # Calculate depth for inline math using MathTextParser
        # This gives us the offset from baseline to bottom of image
        if not is_display:
            try:
                parser = MathTextParser("bitmap")
                # Parse returns a tuple with (ox, oy, width, height, depth, image)
                # For "bitmap" mode, it returns (offset_x, offset_y, width, height, depth, image)
                _, _, _, height, depth, _ = parser.parse(cleaned, dpi=dpi)

                # depth is pixels below baseline, height is total height
                # Convert to em units (12pt font at this DPI)
                font_size_px = 12 * (dpi / 72)
                if height > 0:
                    # depth_em should be negative for CSS vertical-align
                    depth_em = -depth / font_size_px
            except Exception:
                # If depth calculation fails, use a reasonable default
                depth_em = -0.2 if not is_display else 0.0

        # Save with tight bbox and white background
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            dpi=dpi,
            bbox_inches=bbox.transformed(fig.dpi_scale_trans.inverted()),
            facecolor="white",
            edgecolor="none",
            pad_inches=0.02,
        )
        buf.seek(0)
        image_data = buf.read()

        return MathImage(
            latex=latex,
            image_data=image_data,
            image_type="image/png",
            is_display=is_display,
            depth_em=depth_em,
        )

    except Exception:
        # If all else fails, return None and we'll keep the original
        return None
    finally:
        plt.close("all")


def render_latex_to_svg(
    latex: str,
    is_display: bool = False,
) -> MathImage | None:
    """Render a LaTeX equation to an SVG image.

    SVG may be better for scalability on some e-readers.

    Args:
        latex: LaTeX math expression (without $ delimiters)
        is_display: Whether this is a display/block equation

    Returns:
        MathImage with the rendered equation, or None if rendering fails
    """
    if not latex or not latex.strip():
        return None

    # Clean the LaTeX for matplotlib
    cleaned = _clean_latex(latex)

    # Wrap in $ for mathtext
    if not cleaned.startswith("$"):
        cleaned = f"${cleaned}$"

    fig = plt.figure(figsize=(0.01, 0.01))

    try:
        buf = io.BytesIO()
        try:
            math_to_image(cleaned, buf, format="svg")
        except ValueError:
            simple = _simple_latex_fallback(latex)
            if simple:
                math_to_image(f"${simple}$", buf, format="svg")
            else:
                return None

        buf.seek(0)
        image_data = buf.read()

        return MathImage(
            latex=latex,
            image_data=image_data,
            image_type="image/svg+xml",
            is_display=is_display,
        )

    except Exception:
        return None
    finally:
        plt.close(fig)


def extract_latex_from_mathml(mathml_str: str) -> str | None:
    """Extract the original LaTeX from a MathML element.

    arXiv HTML includes the original LaTeX in:
    1. The alttext attribute of <math> elements
    2. <annotation encoding="application/x-tex"> child elements

    Args:
        mathml_str: String containing the MathML element

    Returns:
        The LaTeX string, or None if not found
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(mathml_str, "lxml")
    math_elem = soup.find("math")

    if not math_elem:
        return None

    # Try alttext attribute first (most reliable)
    alttext = math_elem.get("alttext")
    if alttext:
        return alttext

    # Try annotation element
    annotation = math_elem.select_one('annotation[encoding="application/x-tex"]')
    if annotation:
        return annotation.get_text()

    return None
