"""Responsive CSS styles for Kindle devices."""

# Base stylesheet optimized for e-readers
BASE_CSS = """
/* Reset and base styles */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: Georgia, "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    color: #000;
    background: #fff;
    padding: 1em;
    text-align: justify;
    -webkit-hyphens: auto;
    hyphens: auto;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    font-family: Helvetica, Arial, sans-serif;
    font-weight: bold;
    line-height: 1.3;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    text-align: left;
}

h1 {
    font-size: 1.5em;
    margin-top: 0;
    page-break-before: always;
}

h2 {
    font-size: 1.3em;
}

h3 {
    font-size: 1.1em;
}

h4, h5, h6 {
    font-size: 1em;
}

/* Paragraphs */
p {
    margin-bottom: 1em;
    text-indent: 0;
}

p + p {
    text-indent: 1.5em;
    margin-top: 0;
}

/* Links */
a {
    color: #0066cc;
    text-decoration: underline;
}

/* Images */
img {
    max-width: 100%;
    min-width: 60%;
    height: auto;
    display: block;
    margin: 1.5em auto;
}

figure {
    margin: 2em 0;
    text-align: center;
    page-break-inside: avoid;
}

figure img {
    min-width: 70%;
}

figcaption, .ltx_caption {
    font-size: 0.9em;
    font-style: italic;
    margin-top: 0.5em;
    text-align: center;
}

/* Tables */
table {
    max-width: 100%;
    border-collapse: collapse;
    margin: 1.5em 0;
    font-size: 0.85em;
    display: block;
    word-wrap: break-word;
}

th, td {
    border: 1px solid #ccc;
    padding: 0.4em 0.6em;
    text-align: left;
    word-wrap: break-word;
}

th {
    background: #f5f5f5;
    font-weight: bold;
}

/* Ensure table rows and cells don't overflow */
tr {
    page-break-inside: avoid;
}

td, th {
    max-width: 200px;
}

/* Code and preformatted text */
pre, code {
    font-family: "Courier New", Courier, monospace;
    font-size: 0.9em;
    background: #f5f5f5;
}

pre {
    padding: 1em;
    white-space: pre-wrap;
    word-wrap: break-word;
}

code {
    padding: 0.2em 0.4em;
}

/* Blockquotes */
blockquote {
    margin: 1em 2em;
    padding-left: 1em;
    border-left: 3px solid #ccc;
    font-style: italic;
}

/* Lists */
ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.5em;
}

/* Abstract styling */
.abstract {
    margin: 1.5em 0;
    padding: 1em;
    background: #f9f9f9;
    border-left: 4px solid #666;
}

.abstract-title {
    font-weight: bold;
    font-size: 1.1em;
    margin-bottom: 0.5em;
}

/* Author info */
.authors {
    font-style: italic;
    margin-bottom: 1.5em;
    text-align: center;
}

/* Math equations */
math, .ltx_Math, .MathJax {
    font-size: 1em;
    display: inline;
}

.ltx_equation, .equation {
    display: block;
    margin: 1em 0;
    text-align: center;
}

/* LaTeXML specific styles */
.ltx_title {
    font-weight: bold;
}

.ltx_para {
    margin-bottom: 1em;
}

.ltx_item {
    margin-bottom: 0.5em;
}

/* Theorem-like environments */
.theorem-like, .ltx_theorem, .ltx_lemma, .ltx_definition,
.ltx_corollary, .ltx_proposition, .ltx_remark, .ltx_example {
    margin: 1.5em 0;
    padding: 1em;
    background: #f9f9f9;
    border: 1px solid #ddd;
    border-left: 4px solid #666;
    page-break-inside: avoid;
}

.ltx_theorem .ltx_title,
.theorem-like .ltx_title {
    font-weight: bold;
    font-style: italic;
    margin-bottom: 0.5em;
}

.ltx_proof {
    margin: 1em 0;
    padding: 0.5em 1em;
    border-left: 3px solid #999;
    font-style: normal;
}

.ltx_proof .ltx_title {
    font-style: italic;
    font-weight: bold;
}

/* Table wrapper - static layout for e-readers */
.table-wrapper {
    margin: 1.5em 0;
    clear: both;
}

.ltx_tabular, .ltx_table {
    margin: 1.5em auto;
    max-width: 100%;
    font-size: 0.85em;
}

/* LaTeXML table figures */
figure.ltx_figure table,
.ltx_table table {
    margin: 0.5em 0;
}

/* Footnotes */
.footnote-ref {
    text-decoration: none;
    color: #0066cc;
}

.footnote-ref sup {
    font-size: 0.75em;
    vertical-align: super;
}

.footnotes-section {
    margin-top: 2em;
    padding-top: 1em;
    border-top: 1px solid #ccc;
    font-size: 0.9em;
}

.footnotes-section h2 {
    font-size: 1.1em;
    margin-bottom: 1em;
}

.footnotes-section ol {
    padding-left: 1.5em;
}

.footnotes-section li {
    margin-bottom: 0.75em;
}

.footnote-back {
    margin-left: 0.5em;
    text-decoration: none;
}

/* Code blocks */
.code-block, .ltx_listing, .ltx_verbatim {
    background: #f5f5f5;
    padding: 1em;
    margin: 1em 0;
    font-family: "Courier New", Courier, monospace;
    font-size: 0.85em;
    white-space: pre-wrap;
    word-wrap: break-word;
    border: 1px solid #ddd;
    border-radius: 3px;
}

/* Math blocks and equations */
.math-block, .ltx_equationgroup {
    display: block;
    margin: 1.5em 0;
    text-align: center;
    padding: 0.5em 0;
}

/* Equation tables - need special handling */
table.ltx_equation, table.ltx_eqn_table {
    display: table;
    table-layout: fixed;
    width: 100%;
    margin: 1.5em 0;
    border: none;
    font-size: 1em;
}

table.ltx_equation td,
table.ltx_eqn_table td {
    border: none;
    padding: 0.5em 0;
    vertical-align: middle;
}

table.ltx_equation .ltx_eqn_cell,
table.ltx_eqn_table .ltx_eqn_cell {
    border: none;
    background: none;
}

/* Equation layout columns */
.ltx_eqn_center_padleft {
    width: 5%;
}

.ltx_eqn_center_padright {
    width: 5%;
}

/* Main equation content - center column */
td.ltx_align_center {
    text-align: center;
    width: 80%;
}

/* Equation numbers - right column */
.ltx_eqn_eqno, td.ltx_eqn_eqno {
    width: 10%;
    min-width: 3em;
    text-align: right;
    font-size: 0.9em;
    color: #444;
    vertical-align: middle;
    padding-right: 0.5em;
}

.ltx_tag_equation {
    white-space: nowrap;
}

.math-inline, .ltx_Math {
    display: inline;
    font-size: 1em;
}

/* MathML display */
math[display="block"] {
    display: block;
    margin: 1em auto;
    text-align: center;
}

/* Math images (rendered from LaTeX) */
.math-image {
    vertical-align: middle;
    height: auto;
}

.math-image.math-inline {
    display: inline;
    max-height: 1.5em;
    vertical-align: text-bottom;
}

.math-image.math-display {
    display: block;
    max-width: 100%;
    margin: 0 auto;
}

.math-block-img {
    display: block;
    text-align: center;
    margin: 1.5em 0;
    padding: 0.5em 0;
}

/* Citations */
.citation, .ltx_cite {
    font-style: normal;
}

.ltx_cite a {
    color: #0066cc;
}

/* References */
.ltx_bibliography, .references {
    margin-top: 2em;
}

.ltx_bibitem {
    margin-bottom: 1em;
    padding-left: 2em;
    text-indent: -2em;
}

/* Page break hints */
.section, .ltx_section {
    page-break-before: auto;
}

h1 {
    page-break-after: avoid;
}

h2, h3 {
    page-break-after: avoid;
}

figure, table {
    page-break-inside: avoid;
}
"""

# Media queries for Kindle devices
KINDLE_MEDIA_QUERIES = """
/* KF8 format (Kindle Fire, Paperwhite 2+) */
@media amzn-kf8 {
    body {
        font-size: 1em;
    }

    h1 {
        font-size: 1.4em;
    }

    h2 {
        font-size: 1.2em;
    }
}

/* Kindle Fire (color tablets) */
@media amzn-kf8 and (device-aspect-ratio: 1280/800) {
    body {
        font-size: 1.1em;
    }

    img {
        max-width: 100%;
    }
}

/* Kindle Fire HD */
@media amzn-kf8 and (device-aspect-ratio: 1920/1200) {
    body {
        font-size: 1.1em;
    }
}

/* Smaller screens (Kindle Paperwhite, basic Kindle) */
@media screen and (max-width: 600px) {
    body {
        padding: 0.5em;
        font-size: 1em;
    }

    h1 {
        font-size: 1.3em;
    }

    h2 {
        font-size: 1.15em;
    }

    pre {
        font-size: 0.8em;
    }

    table {
        font-size: 0.8em;
    }
}

/* Medium screens (Kindle Oasis, larger tablets) */
@media screen and (min-width: 601px) and (max-width: 1024px) {
    body {
        font-size: 1.05em;
        padding: 1em;
    }
}

/* Larger screens */
@media screen and (min-width: 1025px) {
    body {
        font-size: 1.1em;
        max-width: 800px;
        margin: 0 auto;
        padding: 2em;
    }
}
"""

# Style presets
STYLE_PRESETS = {
    "default": "",
    "compact": """
        body {
            font-size: 0.9em;
            line-height: 1.4;
        }
        p + p {
            text-indent: 1em;
        }
        h1 { font-size: 1.3em; margin-top: 1em; }
        h2 { font-size: 1.15em; }
        h3 { font-size: 1em; }
    """,
    "large-text": """
        body {
            font-size: 1.2em;
            line-height: 1.8;
        }
        h1 { font-size: 1.6em; }
        h2 { font-size: 1.4em; }
        h3 { font-size: 1.2em; }
    """,
}


def get_stylesheet(preset: str = "default") -> str:
    """Get the complete stylesheet for EPUB.

    Args:
        preset: Style preset name ("default", "compact", "large-text")

    Returns:
        Complete CSS stylesheet
    """
    preset_css = STYLE_PRESETS.get(preset, "")
    return f"{BASE_CSS}\n{KINDLE_MEDIA_QUERIES}\n{preset_css}"


def get_cover_css() -> str:
    """Get CSS for the cover page."""
    return """
        body {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            text-align: center;
            padding: 2em;
        }

        h1 {
            font-size: 1.8em;
            margin-bottom: 1em;
            line-height: 1.3;
        }

        .authors {
            font-size: 1.2em;
            font-style: italic;
            margin-bottom: 2em;
        }

        .paper-id {
            font-size: 0.9em;
            color: #666;
        }
    """
