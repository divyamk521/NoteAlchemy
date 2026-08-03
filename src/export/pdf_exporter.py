

from __future__ import annotations

import re
from fpdf import FPDF
from src.export.fonts import resolve_font_set, sanitize_for_font
from src.notes.models import LectureNotes



def _strip_inline(text: str) -> str:
    """Remove inline markdown (bold, italic, code, links)."""
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Truncate very long words (avoid FPDF overflow)
    return text




class _NoteAlchemy(FPDF):
    MARGIN = 18
    PAGE_W = 210  # A4 mm
    CONTENT_W = PAGE_W - 2 * MARGIN

    # Colour palette (RGB)
    C_HEADING1   = (30,  30,  30)
    C_HEADING2   = (50,  50,  50)
    C_HEADING3   = (70,  70,  70)
    C_BODY       = (40,  40,  40)
    C_ACCENT     = (160, 100, 30)   
    C_CODE_BG    = (245, 243, 238)
    C_RULE       = (200, 190, 170)
    C_BLOCKQUOTE = (130, 110, 80)

    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)
        self.set_auto_page_break(auto=True, margin=self.MARGIN)

        # Resolve and register fonts before the first page: header() runs
        # on add_page() and needs a usable family.
        self._font_set = resolve_font_set()
        self._family = self._font_set.family
        self._mono = self._font_set.mono_family
        for style, path in self._font_set.faces:
            family = (
                self._mono if path.stem.endswith("Mono") else self._family
            )
            self.add_font(family=family, style=style, fname=str(path))

        self.add_page()
        self._in_code_block = False

    # ── Header / footer ──────────────────────────────────────────────
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font(self._family, "I", 8)
        self.set_text_color(*self.C_RULE)
        self.cell(0, 6, "NoteAlchemy — Lecture Notes", align="L")
        self.set_text_color(*self.C_BODY)
        self.ln(4)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font(self._family, "", 8)
        self.set_text_color(*self.C_RULE)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")

    # ── Main renderer ─────────────────────────────────────────────────
    def render_markdown(self, markdown: str) -> None:
        """Parse *markdown* line by line and render to PDF.

        Text is sanitised once up front so every downstream path —
        headings, body, code lines, table cells — is safe for the
        resolved font. Without this, an em dash or curly quote in model
        output raises FPDFUnicodeEncodingException mid-render.
        """
        markdown = sanitize_for_font(markdown, self._font_set)
        for raw in markdown.splitlines():
            line = raw.rstrip()

            # Fenced code block toggle
            if line.startswith("```"):
                self._in_code_block = not self._in_code_block
                if self._in_code_block:
                    self.ln(2)
                    self.set_fill_color(*self.C_CODE_BG)
                else:
                    self.ln(2)
                    self.set_fill_color(255, 255, 255)
                continue

            if self._in_code_block:
                self._render_code_line(line)
                continue

            self._render_normal_line(line)

    def _render_code_line(self, line: str) -> None:
        self.set_font(self._mono, "", 8)
        self.set_text_color(*self.C_BODY)
        display = line if line else " "
        self.set_x(self.MARGIN + 4)
        self.multi_cell(
            self.CONTENT_W - 4, 4.5,
            display,
            fill=True,
            align="L",
        )
        self.set_x(self.MARGIN)

    def _render_normal_line(self, line: str) -> None:
        # H1
        if line.startswith("# "):
            self._h1(line[2:].strip())
        # H2
        elif line.startswith("## "):
            self._h2(line[3:].strip())
        # H3
        elif line.startswith("### "):
            self._h3(line[4:].strip())
        # Blockquote
        elif line.startswith("> "):
            self._blockquote(line[2:].strip())
        # Table row
        elif line.startswith("|"):
            self._table_row(line)
        # Bullet
        elif re.match(r"^[-*+] ", line):
            self._bullet(re.sub(r"^[-*+] ", "", line))
        # Numbered list
        elif re.match(r"^\d+\. ", line):
            self._numbered(re.sub(r"^\d+\. ", "", line))
        # Horizontal rule
        elif re.match(r"^[-*_]{3,}\s*$", line):
            self._hr()
        # Blank
        elif not line.strip():
            self.ln(3)
        # Normal paragraph
        else:
            self._body(line)

    # ── Element renderers ────────────────────────────────────────────
    def _h1(self, text: str) -> None:
        self.ln(5)
        self.set_font(self._family, "B", 18)
        self.set_text_color(*self.C_HEADING1)
        self.multi_cell(0, 9, _strip_inline(text), align="L")
        # Underline rule
        y = self.get_y()
        self.set_draw_color(*self.C_ACCENT)
        self.set_line_width(0.6)
        self.line(self.MARGIN, y + 1, self.PAGE_W - self.MARGIN, y + 1)
        self.set_line_width(0.2)
        self.ln(4)
        self._reset_text()

    def _h2(self, text: str) -> None:
        self.ln(4)
        self.set_font(self._family, "B", 14)
        self.set_text_color(*self.C_HEADING2)
        self.multi_cell(0, 7, _strip_inline(text), align="L")
        self.ln(2)
        self._reset_text()

    def _h3(self, text: str) -> None:
        self.ln(3)
        self.set_font(self._family, "BI", 11)
        self.set_text_color(*self.C_HEADING3)
        self.multi_cell(0, 6, _strip_inline(text), align="L")
        self.ln(1)
        self._reset_text()

    def _blockquote(self, text: str) -> None:
        self.set_font(self._family, "I", 10)
        self.set_text_color(*self.C_BLOCKQUOTE)
        self.set_x(self.MARGIN + 6)
        self.multi_cell(self.CONTENT_W - 6, 5.5, _strip_inline(text), align="L")
        self.set_x(self.MARGIN)
        self._reset_text()

    def _body(self, text: str) -> None:
        self._reset_text()
        self.multi_cell(0, 5.5, _strip_inline(text), align="L")

    def _bullet(self, text: str) -> None:
        self._reset_text()
        self.set_x(self.MARGIN + 4)
        self.cell(4, 5.5, "-")
        self.set_x(self.MARGIN + 8)
        self.multi_cell(self.CONTENT_W - 8, 5.5, _strip_inline(text), align="L")
        self.set_x(self.MARGIN)

    def _numbered(self, text: str) -> None:
        self._reset_text()
        self.set_x(self.MARGIN + 4)
        self.multi_cell(self.CONTENT_W - 4, 5.5, _strip_inline(text), align="L")
        self.set_x(self.MARGIN)

    def _table_row(self, line: str) -> None:
        # Skip separator rows like |---|---|
        if re.match(r"^\|[-| :]+\|$", line.strip()):
            return
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not any(cells):
            return
        col_w = self.CONTENT_W / max(len(cells), 1)
        self.set_font(self._family, "", 8)
        self.set_text_color(*self.C_BODY)
        for cell in cells:
            self.cell(col_w, 5.5, _strip_inline(cell)[:50], border=1, align="C")
        self.ln()
        self._reset_text()

    def _hr(self) -> None:
        self.ln(2)
        self.set_draw_color(*self.C_RULE)
        y = self.get_y()
        self.line(self.MARGIN, y, self.PAGE_W - self.MARGIN, y)
        self.ln(3)

    def _reset_text(self) -> None:
        self.set_font(self._family, "", 10)
        self.set_text_color(*self.C_BODY)
        self.set_x(self.MARGIN)


class PDFExporter:
    """Exports notes to PDF bytes."""

    def export(self, notes: LectureNotes) -> bytes:
        """
        Render *notes* to a PDF and return the raw bytes.

        Returns
        -------
        bytes : PDF file content
        """
        pdf = _NoteAlchemy()
        pdf.render_markdown(notes.markdown)
        return bytes(pdf.output())

    def filename(self, notes: LectureNotes) -> str:
        safe = re.sub(r"[^\w\s-]", "", notes.title).strip().replace(" ", "_")[:60]
        return f"{safe}_notes.pdf"
