from __future__ import annotations

import re
from src.notes.models import LectureNotes

def _strip_markdown(text: str) -> str:
    """Remove common markdown syntax, leaving readable plain text."""
    # Remove fenced code blocks (keep content)
    text = re.sub(r"```[a-z]*\n?", "", text)
    text = text.replace("```", "")
    # Bold / italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"_{1,2}(.+?)_{1,2}", r"\1", text)
    # Inline code
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Links [text](url) → text
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Table separator rows
    text = re.sub(r"^\|[-:| ]+\|\s*$", "", text, flags=re.MULTILINE)
    # Blockquote markers
    text = re.sub(r"^> ?", "", text, flags=re.MULTILINE)
    # H1/H2/H3 → text (strip # prefix)
    text = re.sub(r"^#{1,6} +", "", text, flags=re.MULTILINE)
    # Horizontal rules
    text = re.sub(r"^[-*_]{3,}\s*$", "\n", text, flags=re.MULTILINE)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

class TextExporter:
    """Exports notes to plain text."""

    def export(self, notes: LectureNotes) -> bytes:
      
        plain = _strip_markdown(notes.markdown)
        return plain.encode("utf-8")

    def filename(self, notes: LectureNotes) -> str:
        safe = re.sub(r"[^\w\s-]", "", notes.title).strip().replace(" ", "_")[:60]
        return f"{safe}_notes.txt"