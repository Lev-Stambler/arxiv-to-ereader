"""PDF styles for e-reader screens (browser-based rendering)."""

from arxiv_to_ereader.screen_presets import ScreenPreset


def get_pdf_stylesheet(preset: ScreenPreset) -> str:
    """Generate CSS for PDF output optimized for a specific screen size.

    This stylesheet is designed for browser-based rendering via Playwright,
    which provides native MathML support.

    Args:
        preset: Screen preset with dimensions and font settings

    Returns:
        Complete CSS stylesheet
    """
    return f"""
/* Reset */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: Georgia, "Times New Roman", serif;
    font-size: {preset.base_font_pt}pt;
    line-height: 1.5;
    color: #000;
    background: #fff;
    text-align: justify;
    hyphens: auto;
    -webkit-hyphens: auto;
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
    font-family: Helvetica, Arial, sans-serif;
    font-weight: bold;
    line-height: 1.3;
    text-align: left;
    page-break-after: avoid;
}}

h1 {{
    font-size: {preset.base_font_pt * 1.5}pt;
    margin: 0 0 12pt 0;
    page-break-before: always;
}}

h1:first-of-type {{
    page-break-before: avoid;
}}

h2 {{
    font-size: {preset.base_font_pt * 1.3}pt;
    margin: 18pt 0 8pt 0;
}}

h3 {{
    font-size: {preset.base_font_pt * 1.1}pt;
    margin: 14pt 0 6pt 0;
}}

h4, h5, h6 {{
    font-size: {preset.base_font_pt}pt;
    margin: 12pt 0 4pt 0;
}}

/* Paragraphs */
p {{
    margin-bottom: 8pt;
    text-indent: 0;
    orphans: 2;
    widows: 2;
}}

p + p {{
    text-indent: 1.5em;
    margin-top: 0;
}}

/* Links */
a {{
    color: #0066cc;
    text-decoration: underline;
}}

/* Images */
img {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 12pt auto;
}}

figure {{
    margin: 16pt 0;
    text-align: center;
    page-break-inside: avoid;
}}

figcaption, .ltx_caption {{
    font-size: {preset.base_font_pt * 0.9}pt;
    font-style: italic;
    margin-top: 6pt;
    text-align: center;
}}

/* Tables */
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 12pt 0;
    font-size: {preset.base_font_pt * 0.9}pt;
    page-break-inside: avoid;
}}

th, td {{
    border: 0.5pt solid #666;
    padding: 4pt 6pt;
    text-align: left;
}}

th {{
    background: #f0f0f0;
    font-weight: bold;
}}

/* Code */
pre, code {{
    font-family: "Courier New", Courier, monospace;
    font-size: {preset.base_font_pt * 0.85}pt;
    background: #f5f5f5;
}}

pre {{
    padding: 8pt;
    white-space: pre-wrap;
    word-wrap: break-word;
    page-break-inside: avoid;
}}

code {{
    padding: 1pt 3pt;
}}

/* Lists */
ul, ol {{
    margin: 8pt 0;
    padding-left: 1.5em;
}}

li {{
    margin-bottom: 4pt;
}}

/* Cover page */
.cover {{
    text-align: center;
    padding: 20pt 10pt;
    page-break-after: always;
}}

.cover h1 {{
    page-break-before: avoid;
    margin-bottom: 16pt;
    font-size: {preset.base_font_pt * 1.6}pt;
}}

.cover .authors {{
    font-size: {preset.base_font_pt * 1.1}pt;
    font-style: italic;
    margin-bottom: 24pt;
}}

.cover .paper-id {{
    font-size: {preset.base_font_pt * 0.9}pt;
    color: #666;
}}

.cover .date {{
    font-size: {preset.base_font_pt * 0.9}pt;
    color: #666;
    margin-top: 8pt;
}}

/* Abstract */
.abstract {{
    margin: 16pt 0;
    padding: 12pt;
    background: #f8f8f8;
    border-left: 3pt solid #666;
}}

.abstract-title {{
    font-weight: bold;
    margin-bottom: 8pt;
}}

/* Theorem-like environments */
.theorem-like, .ltx_theorem, .ltx_lemma, .ltx_definition,
.ltx_corollary, .ltx_proposition, .ltx_remark, .ltx_example {{
    margin: 14pt 0;
    padding: 10pt;
    background: #f9f9f9;
    border: 0.5pt solid #ddd;
    border-left: 3pt solid #666;
    page-break-inside: avoid;
}}

.ltx_proof {{
    margin: 10pt 0;
    padding: 8pt 10pt;
    border-left: 2pt solid #999;
}}

/* MathML - native browser rendering */
math {{
    font-size: 1em;
}}

math[display="block"] {{
    display: block;
    text-align: center;
    margin: 12pt 0;
}}

/* Equation tables */
table.ltx_equation, table.ltx_eqn_table {{
    border: none;
    margin: 12pt 0;
    width: 100%;
}}

table.ltx_equation td,
table.ltx_eqn_table td {{
    border: none;
    padding: 4pt 0;
    vertical-align: middle;
}}

.ltx_eqn_cell {{
    text-align: center;
}}

.ltx_eqn_eqno {{
    text-align: right;
    font-size: {preset.base_font_pt * 0.9}pt;
    color: #444;
    width: 10%;
}}

/* Citations */
.citation, .ltx_cite {{
    font-style: normal;
}}

/* References */
.ltx_bibliography, .references {{
    margin-top: 20pt;
}}

.ltx_bibitem {{
    margin-bottom: 8pt;
    padding-left: 2em;
    text-indent: -2em;
    font-size: {preset.base_font_pt * 0.9}pt;
}}

/* Footnotes section */
.footnotes-section {{
    margin-top: 20pt;
    padding-top: 10pt;
    border-top: 0.5pt solid #ccc;
    font-size: {preset.base_font_pt * 0.9}pt;
}}

.footnotes-section h2 {{
    font-size: {preset.base_font_pt * 1.1}pt;
    margin-bottom: 10pt;
}}

/* Footnote references */
.footnote-ref {{
    text-decoration: none;
    color: #0066cc;
}}

.footnote-ref sup {{
    font-size: 0.75em;
}}

/* LaTeXML specific */
.ltx_para {{
    margin-bottom: 8pt;
}}

.ltx_item {{
    margin-bottom: 4pt;
}}

/* Code blocks */
.code-block, .ltx_listing, .ltx_verbatim {{
    background: #f5f5f5;
    padding: 8pt;
    margin: 10pt 0;
    font-family: "Courier New", Courier, monospace;
    font-size: {preset.base_font_pt * 0.85}pt;
    white-space: pre-wrap;
    word-wrap: break-word;
    border: 0.5pt solid #ddd;
}}

/* Blockquotes */
blockquote {{
    margin: 10pt 15pt;
    padding-left: 10pt;
    border-left: 2pt solid #ccc;
    font-style: italic;
}}

/* Section breaks */
.ltx_section {{
    page-break-before: auto;
}}

/* Table wrapper */
.table-wrapper {{
    margin: 12pt 0;
}}

/* LaTeXML span-based tables */
.ltx_tabular {{
    display: table;
    border-collapse: collapse;
    margin: 8pt auto;
    font-size: {preset.base_font_pt * 0.85}pt;
}}

.ltx_tr {{
    display: table-row;
}}

.ltx_td, .ltx_th {{
    display: table-cell;
    padding: 3pt 5pt;
    text-align: left;
    vertical-align: middle;
}}

/* LaTeXML table borders */
.ltx_border_t {{ border-top: 0.5pt solid #444; }}
.ltx_border_b {{ border-bottom: 0.5pt solid #444; }}
.ltx_border_l {{ border-left: 0.5pt solid #444; }}
.ltx_border_r {{ border-right: 0.5pt solid #444; }}
.ltx_border_tt {{ border-top: 1pt solid #000; }}
.ltx_border_bb {{ border-bottom: 1pt solid #000; }}

/* LaTeXML table figure */
.ltx_table {{
    margin: 12pt auto;
    page-break-inside: avoid;
}}

/* Transform containers - reset transforms for e-reader readability */
.ltx_transformed_outer {{
    display: block;
    margin: 8pt auto;
    max-width: 100%;
    overflow-x: auto;
    /* Reset fixed dimensions from LaTeXML */
    width: auto !important;
    height: auto !important;
    vertical-align: baseline !important;
}}

.ltx_transformed_inner {{
    display: block;
    /* Reset scaling transforms - we want full-size content on e-readers */
    transform: none !important;
}}

/* Tables should be allowed to overflow with scrolling if needed */
.ltx_table .ltx_transformed_outer {{
    overflow-x: auto;
}}

/* SVG figures (algorithms, diagrams) */
svg.ltx_picture {{
    max-width: 100%;
    height: auto;
    display: block;
    margin: 10pt auto;
}}

/* Foreign objects in SVG need proper sizing */
svg foreignobject {{
    overflow: visible;
}}

.ltx_foreignobject_container {{
    display: block;
}}

/* Algorithm boxes */
.ltx_figure svg {{
    max-width: 100%;
    height: auto;
}}

/* Print-specific */
@media print {{
    body {{
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
    }}

    .cover {{
        page-break-after: always;
    }}

    h1, h2, h3, h4, h5, h6 {{
        page-break-after: avoid;
    }}

    figure, table, pre {{
        page-break-inside: avoid;
    }}
}}
"""
