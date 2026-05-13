"""this file is a pre orchestrstion design for the pdf export, it contains the logic to convert markdown to text and to pdf, it is used by the PDFExporter class in pdf_exporter.py"""
import io
import re
from fpdf import FPDF

#notes to text
def notes_to_text(notes_markdown: str) -> bytes:
    """Return notes as UTF-8 encoded plain text (strips markdown syntax)."""
    text = notes_markdown
    # Remove bold/italic markers
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # Remove inline code backticks
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Remove fenced code blocks markers
    text = re.sub(r"```[a-z]*\n?", "", text)
    text = text.replace("```", "")
    # Remove table separators
    text = re.sub(r"\|[-: ]+\|[-| :]*\n", "", text)
    return text.encode("utf-8")

class _NotesPDF(FPDF):
    """Custom FPDF subclass with styled rendering for our notes."""

    MARGIN = 15

    def __init__(self):
        super().__init__()
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)
        self.set_auto_page_break(auto=True, margin=self.MARGIN)
        self.add_page()
        # Use built-in Helvetica family (always available)
        self.set_font("Helvetica", size=11)

    # ------------------------------------------------------------------
    def _write_line(self, line: str):
        """Render a single markdown line with basic formatting."""

        # H1
        if line.startswith("# "):
            self.set_font("Helvetica", "B", 18)
            self.ln(4)
            self.multi_cell(0, 8, line[2:].strip(), align="L")
            self.ln(2)
            self.set_font("Helvetica", size=11)
            return

        # H2
        if line.startswith("## "):
            self.set_font("Helvetica", "B", 14)
            self.ln(3)
            self.multi_cell(0, 7, line[3:].strip(), align="L")
            self.ln(1)
            self.set_font("Helvetica", size=11)
            return

        # H3
        if line.startswith("### "):
            self.set_font("Helvetica", "BI", 12)
            self.ln(2)
            self.multi_cell(0, 6, line[4:].strip(), align="L")
            self.set_font("Helvetica", size=11)
            return

        # Bullet / list item
        if re.match(r"^[-*+] ", line) or re.match(r"^\d+\. ", line):
            indent = 8
            text = re.sub(r"^[-*+] ", "- ", line)
            text = re.sub(r"^\d+\. ", lambda m: m.group(0), text)
            # strip inline markdown
            text = self._strip_inline(text)
            self.set_x(self.MARGIN + indent)
            self.multi_cell(0, 5.5, text, align="L")
            self.set_x(self.MARGIN)
            return

        # Separator line
        if re.match(r"^[-=]{3,}$", line.strip()):
            self.ln(1)
            self.line(self.MARGIN, self.get_y(), self.w - self.MARGIN, self.get_y())
            self.ln(2)
            return

        # Table row
        if line.startswith("|"):
            self._render_table_row(line)
            return

        # Blank line
        if not line.strip():
            self.ln(3)
            return

        # Normal paragraph text
        text = self._strip_inline(line)
        self.multi_cell(0, 5.5, text, align="L")

    def _strip_inline(self, text: str) -> str:
        """Remove inline markdown (bold, italic, code, links)."""
        text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        return text

    def _render_table_row(self, line: str):
        """Render a markdown table row."""
        # Skip separator rows like |---|---|
        if re.match(r"^\|[-| :]+\|$", line.strip()):
            return
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not any(cells):
            return
        col_w = (self.w - 2 * self.MARGIN) / max(len(cells), 1)
        self.set_font("Helvetica", size=9)
        for cell in cells:
            self.cell(col_w, 6, self._strip_inline(cell)[:40], border=1)
        self.ln()
        self.set_font("Helvetica", size=11)

    # ------------------------------------------------------------------
    def render_markdown(self, markdown: str):
        """Parse and render full markdown notes."""
        in_code_block = False
        for raw_line in markdown.splitlines():
            if raw_line.startswith("```"):
                in_code_block = not in_code_block
                if in_code_block:
                    self.set_font("Courier", size=9)
                    self.set_fill_color(240, 240, 240)
                else:
                    self.set_font("Helvetica", size=11)
                    self.set_fill_color(255, 255, 255)
                continue
            if in_code_block:
                self.set_x(self.MARGIN + 4)
                self.multi_cell(0, 5, raw_line if raw_line else " ", fill=True)
                self.set_x(self.MARGIN)
            else:
                self._write_line(raw_line)


def notes_to_pdf(notes_markdown: str) -> bytes:
    """Return notes rendered as a PDF byte-string."""
    pdf = _NotesPDF()
    pdf.render_markdown(notes_markdown)
    return bytes(pdf.output())
