from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field, field_validator

class Section(BaseModel):
    """One top-level section in the notes outline."""

    heading: str = Field(..., min_length=1)
    sub_headings: list[str] = Field(default_factory=list)

    @field_validator("sub_headings")
    @classmethod
    def _non_empty_sub_headings(cls, v: list[str]) -> list[str]:#runs automatically and cleans empty subheadings
        return [sh for sh in v if sh.strip()]
    
class GlossaryEntry(BaseModel):
    """A single term–definition pair in the glossary."""

    term: str
    definition: str

class NotesStructure(BaseModel):
    """
    The hierarchical outline produced by the structure-generation step.
    Validated directly from the LLM JSON response.
    """

    title: str = Field(..., min_length=1)
    summary: Optional[str] = None
    key_concepts: list[str] = Field(default_factory=list)
    sections: list[Section] = Field(..., min_length=1)


class SectionContent(BaseModel):
    """Holds the generated markdown content for one section."""

    section: Section
    content: str  # raw markdown

class LectureNotes(BaseModel):
    """
    Fully assembled lecture notes: structure + per-section content
    + optional glossary.
    """

    structure: NotesStructure
    sections: list[SectionContent]
    glossary: list[GlossaryEntry] = Field(default_factory=list)

    

    @property
    def title(self) -> str:
        return self.structure.title

    @property
    def markdown(self) -> str:
        """Return the full notes as a single markdown document."""
        lines: list[str] = []

        lines.append(f"# {self.structure.title}\n")

        if self.structure.summary:
            lines.append(f"> {self.structure.summary}\n")

        if self.structure.key_concepts:
            lines.append("## Key Concepts\n")
            for concept in self.structure.key_concepts:
                lines.append(f"- **{concept}**")
            lines.append("")

        for sc in self.sections:
            lines.append(f"## {sc.section.heading}\n")
            lines.append(sc.content)
            lines.append("")

        if self.glossary:
            lines.append("---\n## Glossary\n")
            for entry in self.glossary:
                lines.append(f"**{entry.term}**  \n{entry.definition}\n")

        return "\n".join(lines)

    @property
    def word_count(self) -> int:
        return len(self.markdown.split())
