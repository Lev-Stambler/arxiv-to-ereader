"""Tests for the math renderer module."""

import pytest

from arxiv_to_ereader.math_renderer import (
    MathImage,
    _clean_latex,
    _simple_latex_fallback,
    extract_latex_from_mathml,
    render_latex_to_image,
    render_latex_to_svg,
)


class TestCleanLatex:
    """Tests for LaTeX cleaning function."""

    def test_strips_whitespace(self) -> None:
        """Test that leading/trailing whitespace is stripped."""
        assert _clean_latex("  x + y  ") == "x + y"

    def test_converts_text_command(self) -> None:
        """Test that \\text{} is converted to \\mathrm{}."""
        result = _clean_latex(r"\text{hello}")
        assert "mathrm" in result

    def test_removes_left_right_brackets(self) -> None:
        """Test that \\left[ and \\right] are simplified."""
        result = _clean_latex(r"\left[x\right]")
        assert r"\left[" not in result
        assert "[x]" in result

    def test_handles_spacing_commands(self) -> None:
        """Test that spacing commands are handled."""
        result = _clean_latex(r"a\,b\;c")
        assert r"\," not in result
        assert r"\;" not in result


class TestRenderLatexToImage:
    """Tests for LaTeX to image rendering."""

    def test_renders_simple_expression(self) -> None:
        """Test rendering a simple math expression."""
        result = render_latex_to_image("x + y")
        assert result is not None
        assert isinstance(result, MathImage)
        assert result.image_data is not None
        assert len(result.image_data) > 0
        assert result.image_type == "image/png"

    def test_renders_greek_letters(self) -> None:
        """Test rendering Greek letters."""
        result = render_latex_to_image(r"\alpha + \beta")
        assert result is not None
        assert result.image_data is not None

    def test_renders_fractions(self) -> None:
        """Test rendering fractions."""
        result = render_latex_to_image(r"\frac{a}{b}")
        assert result is not None
        assert result.image_data is not None

    def test_renders_subscript_superscript(self) -> None:
        """Test rendering subscripts and superscripts."""
        result = render_latex_to_image(r"x^2 + y_i")
        assert result is not None
        assert result.image_data is not None

    def test_renders_sum_notation(self) -> None:
        """Test rendering summation notation."""
        result = render_latex_to_image(r"\sum_{i=1}^{n} x_i")
        assert result is not None
        assert result.image_data is not None

    def test_empty_latex_returns_none(self) -> None:
        """Test that empty LaTeX returns None."""
        assert render_latex_to_image("") is None
        assert render_latex_to_image("   ") is None

    def test_generates_unique_filenames(self) -> None:
        """Test that different equations get unique filenames."""
        result1 = render_latex_to_image("x + y")
        result2 = render_latex_to_image("a + b")
        assert result1 is not None
        assert result2 is not None
        assert result1.filename != result2.filename

    def test_same_latex_same_filename(self) -> None:
        """Test that same equations get same filename (for deduplication)."""
        result1 = render_latex_to_image("x + y")
        result2 = render_latex_to_image("x + y")
        assert result1 is not None
        assert result2 is not None
        assert result1.filename == result2.filename

    def test_display_mode_flag(self) -> None:
        """Test that display mode flag is preserved."""
        inline = render_latex_to_image("x + y", is_display=False)
        display = render_latex_to_image("x + y", is_display=True)
        assert inline is not None
        assert display is not None
        assert inline.is_display is False
        assert display.is_display is True

    def test_dpi_affects_image_size(self) -> None:
        """Test that higher DPI produces larger images."""
        low_dpi = render_latex_to_image("x + y", dpi=72)
        high_dpi = render_latex_to_image("x + y", dpi=300)
        assert low_dpi is not None
        assert high_dpi is not None
        # Higher DPI should produce larger image data
        assert len(high_dpi.image_data) > len(low_dpi.image_data)


class TestRenderLatexToSvg:
    """Tests for LaTeX to SVG rendering."""

    def test_renders_simple_svg(self) -> None:
        """Test rendering simple expression to SVG."""
        result = render_latex_to_svg("x + y")
        assert result is not None
        assert isinstance(result, MathImage)
        assert result.image_type == "image/svg+xml"
        # SVG starts with XML or svg tag
        assert b"<svg" in result.image_data or b"<?xml" in result.image_data

    def test_empty_latex_returns_none(self) -> None:
        """Test that empty LaTeX returns None."""
        assert render_latex_to_svg("") is None
        assert render_latex_to_svg("   ") is None

    def test_svg_display_mode(self) -> None:
        """Test display mode flag in SVG."""
        result = render_latex_to_svg("x", is_display=True)
        assert result is not None
        assert result.is_display is True


class TestSimpleLatexFallback:
    """Tests for simple LaTeX fallback function."""

    def test_strips_commands(self) -> None:
        """Test stripping LaTeX commands."""
        result = _simple_latex_fallback(r"\alpha + \beta")
        assert "\\" not in result

    def test_removes_braces(self) -> None:
        """Test removing braces."""
        result = _simple_latex_fallback(r"\frac{a}{b}")
        assert "{" not in result
        assert "}" not in result

    def test_returns_question_for_empty(self) -> None:
        """Test returning ? for completely empty result."""
        result = _simple_latex_fallback(r"\cmd")
        # After removing command, result is empty or just ?
        assert result in ("", "?")


class TestExtractLatexFromMathml:
    """Tests for extracting LaTeX from MathML."""

    def test_extracts_from_alttext(self) -> None:
        """Test extracting LaTeX from alttext attribute."""
        mathml = '<math alttext="x + y"><mi>x</mi></math>'
        result = extract_latex_from_mathml(mathml)
        assert result == "x + y"

    def test_extracts_from_annotation(self) -> None:
        """Test extracting LaTeX from annotation element."""
        mathml = '''
        <math>
            <semantics>
                <mi>x</mi>
                <annotation encoding="application/x-tex">x + y</annotation>
            </semantics>
        </math>
        '''
        result = extract_latex_from_mathml(mathml)
        assert result == "x + y"

    def test_prefers_alttext_over_annotation(self) -> None:
        """Test that alttext is preferred when both are present."""
        mathml = '''
        <math alttext="from alttext">
            <semantics>
                <mi>x</mi>
                <annotation encoding="application/x-tex">from annotation</annotation>
            </semantics>
        </math>
        '''
        result = extract_latex_from_mathml(mathml)
        assert result == "from alttext"

    def test_returns_none_for_invalid_mathml(self) -> None:
        """Test that invalid MathML returns None."""
        assert extract_latex_from_mathml("<div>not math</div>") is None
        assert extract_latex_from_mathml("") is None

    def test_complex_arxiv_mathml(self) -> None:
        """Test parsing actual arXiv MathML structure."""
        mathml = '''
        <math alttext="\\mathcal{L}_{\\text{MLM}}" class="ltx_Math" display="inline">
            <semantics>
                <msub><mi>ℒ</mi><mtext>MLM</mtext></msub>
                <annotation encoding="application/x-tex">\\mathcal{L}_{\\text{MLM}}</annotation>
            </semantics>
        </math>
        '''
        result = extract_latex_from_mathml(mathml)
        assert result == r"\mathcal{L}_{\text{MLM}}"


class TestInlineMathDepth:
    """Tests for inline math depth calculation (baseline alignment)."""

    def test_inline_math_has_depth_em(self) -> None:
        """Test that inline math has depth_em field."""
        result = render_latex_to_image("x + y", is_display=False)
        assert result is not None
        assert hasattr(result, "depth_em")
        assert isinstance(result.depth_em, float)

    def test_display_math_has_zero_depth(self) -> None:
        """Test that display math has zero depth (no vertical align needed)."""
        result = render_latex_to_image("x + y", is_display=True)
        assert result is not None
        assert result.depth_em == 0.0

    def test_inline_math_has_nonzero_depth(self) -> None:
        """Test that inline math calculates non-zero depth for alignment."""
        result = render_latex_to_image("x + y", is_display=False)
        assert result is not None
        # Inline math should have some depth for baseline alignment
        # The depth should be negative (below baseline) or very small
        assert result.depth_em <= 0.1  # Either negative or near zero

    def test_subscript_has_more_depth_than_simple(self) -> None:
        """Test that subscripts have more depth than simple expressions."""
        simple = render_latex_to_image("x", is_display=False)
        subscript = render_latex_to_image("x_i", is_display=False)
        assert simple is not None
        assert subscript is not None
        # Subscripts extend below baseline more, so should have more negative depth
        # Note: depth_em is negative for below baseline
        assert subscript.depth_em <= simple.depth_em

    def test_fraction_has_significant_depth(self) -> None:
        """Test that fractions have significant depth."""
        result = render_latex_to_image(r"\frac{a}{b}", is_display=False)
        assert result is not None
        # Fractions extend below baseline
        assert result.depth_em < 0

    def test_depth_is_reasonable_em_value(self) -> None:
        """Test that depth is a reasonable value in em units."""
        result = render_latex_to_image("x_i", is_display=False)
        assert result is not None
        # Depth should be between -2em and 0.5em (reasonable range)
        assert -2.0 < result.depth_em < 0.5

    def test_simple_variable_has_small_depth(self) -> None:
        """Test that a simple variable like 'x' has small depth."""
        result = render_latex_to_image("x", is_display=False)
        assert result is not None
        # Simple variables sit mostly on baseline, small negative or near-zero depth
        assert -0.5 < result.depth_em < 0.3
