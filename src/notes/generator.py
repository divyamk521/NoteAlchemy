
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from pydantic import ValidationError

from config.settings import get_settings
from src.llm.completion import LLMClient, CompletionError
from src.llm import prompts
from src.notes.models import (
    LectureNotes,
    NotesStructure,
    SectionContent,
    GlossaryEntry,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Type alias for a progress-callback: receives (current_step, total_steps, message)
ProgressCallback = Callable[[int, int, str], None]


@dataclass
class GenerationStats:
    """Timing and token metadata collected during generation."""

    structure_time: float = 0.0
    content_times: list[float] = field(default_factory=list)
    glossary_time: float = 0.0
    total_sections: int = 0

    @property
    def total_time(self) -> float:
        return self.structure_time + sum(self.content_times) + self.glossary_time

    @property
    def avg_section_time(self) -> float:
        if not self.content_times:
            return 0.0
        return sum(self.content_times) / len(self.content_times)
    
class NotesGenerator:
    """
    Generates :class:`~src.notes.models.LectureNotes` from a transcript.

    Parameters
    ----------
    llm : LLMClient
        Initialised LLM client (injected for testability).
    generate_glossary : bool
        Whether to append a glossary section (extra LLM call).
    on_progress : ProgressCallback | None
        Optional callback invoked after each pipeline step.
        Signature: ``(current_step: int, total_steps: int, message: str) -> None``
    """

    def __init__(
        self,
        llm: LLMClient,
        generate_glossary: bool = True,
        on_progress: Optional[ProgressCallback] = None,
    ) -> None:
        self._llm = llm
        self._generate_glossary = generate_glossary
        self._on_progress = on_progress or (lambda *_: None)

    # ------------------------------------------------------------------ #
    #  Main entry point
    # ------------------------------------------------------------------ #

    def generate(self, transcript: str) -> tuple[LectureNotes, GenerationStats]:
        """
        Run the full pipeline and return ``(LectureNotes, GenerationStats)``.

        Parameters
        ----------
        transcript : str
            Full lecture transcript text.

        Raises
        ------
        CompletionError
            On unrecoverable LLM failure.
        ValidationError
            If the LLM returns structurally invalid JSON.
        """
        import time

        stats = GenerationStats()

        # ── Step 1: Generate structure ────────────────────────────────
        total_steps = 2 + 1  # structure + sections placeholder + glossary
        self._on_progress(1, total_steps, "Analysing lecture and building outline…")

        t0 = time.perf_counter()
        structure = self._build_structure(transcript)
        stats.structure_time = time.perf_counter() - t0
        stats.total_sections = len(structure.sections)

        logger.info(
            f"Structure built: '{structure.title}' "
            f"with {len(structure.sections)} sections"
        )

        # Update total steps now we know section count
        total_steps = 1 + len(structure.sections) + (1 if self._generate_glossary else 0)

        # ── Step 2: Generate section content ─────────────────────────
        section_contents: list[SectionContent] = []
        for i, section in enumerate(structure.sections):
            step_num = i + 2
            self._on_progress(
                step_num,
                total_steps,
                f"Writing section {i + 1}/{len(structure.sections)}: {section.heading}",
            )
            t0 = time.perf_counter()
            content = self._build_section_content(transcript, structure, section)
            stats.content_times.append(time.perf_counter() - t0)
            section_contents.append(SectionContent(section=section, content=content))
            logger.debug(f"Section '{section.heading}' written ({len(content)} chars)")

        # ── Step 3: Glossary (optional) ───────────────────────────────
        glossary: list[GlossaryEntry] = []
        if self._generate_glossary and structure.key_concepts:
            self._on_progress(total_steps, total_steps, "Building glossary…")
            t0 = time.perf_counter()
            glossary = self._build_glossary(transcript, structure.key_concepts)
            stats.glossary_time = time.perf_counter() - t0
            logger.debug(f"Glossary built: {len(glossary)} entries")

        notes = LectureNotes(
            structure=structure,
            sections=section_contents,
            glossary=glossary,
        )
        logger.success(
            f"Notes complete: '{notes.title}' — "
            f"{notes.word_count} words in {stats.total_time:.1f}s"
        )
        return notes, stats

    # ------------------------------------------------------------------ #
    #  Private helpers — each maps to one LLM call
    # ------------------------------------------------------------------ #

    def _build_structure(self, transcript: str) -> NotesStructure:
        raw = self._llm.complete_json(
            model=settings.structure_model,
            system=prompts.STRUCTURE_SYSTEM,
            user=prompts.build_structure_prompt(transcript),
            temperature=settings.structure_temperature,
            max_tokens=settings.structure_max_tokens,
        )
        try:
            return NotesStructure.model_validate(raw)
        except ValidationError as exc:
            raise CompletionError(
                f"Structure JSON failed pydantic validation: {exc}"
            ) from exc

    def _build_section_content(
        self,
        transcript: str,
        structure: NotesStructure,
        section,
    ) -> str:
        return self._llm.complete(
            model=settings.content_model,
            system=prompts.CONTENT_SYSTEM,
            user=prompts.build_content_prompt(
                transcript,
                structure.model_dump(),
                section.model_dump(),
            ),
            temperature=settings.content_temperature,
            max_tokens=settings.content_max_tokens,
        )

    def _build_glossary(
        self,
        transcript: str,
        key_concepts: list[str],
    ) -> list[GlossaryEntry]:
        try:
            raw = self._llm.complete_json(
                model=settings.content_model,
                system=prompts.GLOSSARY_SYSTEM,
                user=prompts.build_glossary_prompt(transcript, key_concepts),
                temperature=0.3,
                max_tokens=1200,
            )
            entries = raw.get("glossary", [])
            return [GlossaryEntry(**e) for e in entries if "term" in e]
        except Exception as exc:
            # Glossary is non-critical — log and continue
            logger.warning(f"Glossary generation failed (non-fatal): {exc}")
            return []
