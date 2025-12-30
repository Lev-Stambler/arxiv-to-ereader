#!/usr/bin/env python3
"""Visual test for inline math rendering.

Generates a test page with various inline math scenarios and screenshots it.
Run this script, then ask Claude to analyze the screenshot.

Usage:
    uv run python scripts/visual_math_test.py
    # Then ask Claude: "Look at screenshots/math_test.png and check if inline math looks correct"
"""

import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from arxiv_to_ereader.converter import _convert_math_to_images
from arxiv_to_ereader.styles import get_stylesheet


def generate_test_html() -> str:
    """Generate HTML with various inline math test cases."""

    test_cases = [
        ("Simple variable", "The variable <math alttext=\"x\" display=\"inline\"><mi>x</mi></math> is important."),
        ("Subscript", "We define <math alttext=\"x_i\" display=\"inline\"><mi>x</mi></math> as the i-th element."),
        ("Superscript", "Calculate <math alttext=\"x^2\" display=\"inline\"><mi>x</mi></math> for the result."),
        ("Fraction", "The ratio <math alttext=\"\\frac{a}{b}\" display=\"inline\"><mi>x</mi></math> is less than one."),
        ("Greek letter", "Let <math alttext=\"\\alpha\" display=\"inline\"><mi>α</mi></math> be the learning rate."),
        ("Sum notation", "Compute <math alttext=\"\\sum_{i=1}^{n}\" display=\"inline\"><mi>Σ</mi></math> over all elements."),
        ("Multiple inline", "Given <math alttext=\"x\" display=\"inline\"><mi>x</mi></math> and <math alttext=\"y\" display=\"inline\"><mi>y</mi></math>, find <math alttext=\"x + y\" display=\"inline\"><mi>z</mi></math>."),
        ("Mixed text", "The equation <math alttext=\"E = mc^2\" display=\"inline\"><mi>E</mi></math> shows mass-energy equivalence."),
        ("Beta params", "We set <math alttext=\"\\beta_1\" display=\"inline\"><mi>β</mi></math> = 0.9 and <math alttext=\"\\beta_2\" display=\"inline\"><mi>β</mi></math> = 0.999."),
    ]

    # Convert math in each test case
    rows = []
    all_math_images = {}

    for name, html in test_cases:
        converted, all_math_images = _convert_math_to_images(html, all_math_images)
        rows.append(f"""
        <tr>
            <td style="padding: 10px; border: 1px solid #ccc; font-weight: bold;">{name}</td>
            <td style="padding: 10px; border: 1px solid #ccc; font-size: 16px; line-height: 1.6;">{converted}</td>
        </tr>
        """)

    # Create base64 encoded images for embedding
    import base64
    style_block = ""
    for latex, math_img in all_math_images.items():
        # We'll reference images by their src path
        pass

    css = get_stylesheet()

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Inline Math Visual Test</title>
    <style>
{css}
body {{
    font-family: Georgia, serif;
    font-size: 16px;
    line-height: 1.6;
    padding: 20px;
    max-width: 800px;
    margin: 0 auto;
    background: white;
}}
h1 {{
    color: #333;
    border-bottom: 2px solid #333;
    padding-bottom: 10px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}}
.reference {{
    background: #f5f5f5;
    padding: 15px;
    margin: 20px 0;
    border-left: 4px solid #666;
}}
.pass {{ color: green; }}
.fail {{ color: red; }}
    </style>
</head>
<body>
    <h1>Inline Math Visual Test</h1>

    <div class="reference">
        <strong>What to check:</strong>
        <ul>
            <li>Inline math should be approximately the same height as surrounding text</li>
            <li>Math should sit on the text baseline (not floating above or below)</li>
            <li>Subscripts/fractions may extend slightly below the baseline</li>
            <li>There should be no huge gaps or size mismatches</li>
        </ul>
    </div>

    <h2>Test Cases</h2>
    <table>
        <tr>
            <th style="padding: 10px; border: 1px solid #ccc; text-align: left;">Test</th>
            <th style="padding: 10px; border: 1px solid #ccc; text-align: left;">Rendered Output</th>
        </tr>
        {"".join(rows)}
    </table>

    <h2>Paragraph Test</h2>
    <p>
        This is a paragraph with multiple inline math expressions to test flow.
        The learning rate <math alttext="\\alpha" display="inline"><mi>α</mi></math> is set to 0.001.
        We use Adam optimizer with <math alttext="\\beta_1" display="inline"><mi>β</mi></math> = 0.9.
        The loss function <math alttext="L" display="inline"><mi>L</mi></math> is minimized over
        <math alttext="n" display="inline"><mi>n</mi></math> epochs.
    </p>

    <h2>Comparison Line</h2>
    <p style="font-size: 18px;">
        Regular text height: Xxy | Math: <math alttext="X" display="inline"><mi>X</mi></math><math alttext="x" display="inline"><mi>x</mi></math><math alttext="y" display="inline"><mi>y</mi></math> | Should match!
    </p>
</body>
</html>
"""

    # Convert all the remaining math
    final_html, _ = _convert_math_to_images(html, all_math_images)

    return final_html, all_math_images


def main():
    """Generate and screenshot the visual test."""
    print("Generating test HTML with inline math...")
    html_content, math_images = generate_test_html()

    # Create screenshots directory
    screenshots_dir = Path("screenshots")
    screenshots_dir.mkdir(exist_ok=True)

    # Write HTML to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        # Embed math images as base64
        import base64
        for latex, math_img in math_images.items():
            b64 = base64.b64encode(math_img.image_data).decode()
            data_uri = f"data:image/png;base64,{b64}"
            html_content = html_content.replace(f'src="math/{math_img.filename}"', f'src="{data_uri}"')

        f.write(html_content)
        temp_path = f.name

    print(f"Wrote test HTML to {temp_path}")

    # Screenshot with Playwright
    print("Taking screenshot with Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 900, "height": 1200})
        page.goto(f"file://{temp_path}")
        page.wait_for_load_state("networkidle")

        # Take screenshot
        screenshot_path = screenshots_dir / "math_test.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        browser.close()

    # Clean up
    Path(temp_path).unlink()

    print(f"\n✓ Screenshot saved to: {screenshot_path}")
    print("\nTo analyze with Claude, ask:")
    print('  "Look at screenshots/math_test.png - does the inline math look correct?"')


if __name__ == "__main__":
    main()
