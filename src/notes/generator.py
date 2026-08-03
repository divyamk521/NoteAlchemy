
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    """Timing metadata collected during generation.

    ``content_times`` holds each section's own duration. Because sections
    run concurrently, their sum is *not* elapsed time — ``sections_wall_time``
    is the real cost of that phase, and ``total_time`` is built from it.
    """

    structure_time: float = 0.0
    content_times: list[float] = field(default_factory=list)
    sections_wall_time: float = 0.0
    glossary_time: float = 0.0
    total_sections: int = 0

    @property
    def total_time(self) -> float:
        """Wall-clock time for the whole pipeline."""
        return self.structure_time + self.sections_wall_time + self.glossary_time

    @property
    def avg_section_time(self) -> float:
        if not self.content_times:
            return 0.0
        return sum(self.content_times) / len(self.content_times)

    @property
    def sections_speedup(self) -> float:
        """How much concurrency saved on the section phase (1.0 = none)."""
        if not self.sections_wall_time:
            return 1.0
        return sum(self.content_times) / self.sections_wall_time


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

        # ── Step 2: Generate section content (concurrently) ───────────
        # Each section depends only on (transcript, structure, section),
        # so they are independent calls. Running them one at a time made
        # the section phase N times slower than its critical path.
        section_contents = self._build_all_sections(
            transcript, structure, stats, total_steps
        )

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

    def _build_all_sections(
        self,
        transcript: str,
        structure: NotesStructure,
        stats: GenerationStats,
        total_steps: int,
    ) -> list[SectionContent]:
        """Generate every section's content concurrently, preserving order.

        Futures are submitted here and drained with ``as_completed`` on the
        *calling* thread, so ``self._on_progress`` never fires from a worker.
        That matters because the Streamlit callback touches widgets, which
        only works on the thread running the script.

        Sections finish out of order, so results are placed by index rather
        than appended.
        """
        sections = structure.sections
        n = len(sections)
        workers = max(1, min(settings.max_concurrent_sections, n))

        results: list[Optional[str]] = [None] * n
        durations: list[float] = [0.0] * n
        completed = 0

        logger.info(f"Writing {n} sections with {workers} concurrent workers")
        wall_start = time.perf_counter()

        def work(index: int) -> tuple[int, str, float]:
            t0 = time.perf_counter()
            content = self._build_section_content(
                transcript, structure, sections[index]
            )
            return index, content, time.perf_counter() - t0

        with ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix="notealchemy-section"
        ) as pool:
            futures = {pool.submit(work, i): i for i in range(n)}
            try:
                for future in as_completed(futures):
                    index, content, elapsed = future.result()
                    results[index] = content
                    durations[index] = elapsed
                    completed += 1
                    logger.debug(
                        f"Section '{sections[index].heading}' written "
                        f"({len(content)} chars in {elapsed:.1f}s)"
                    )
                    # Progress reflects completion count, not position,
                    # because sections do not finish in order.
                    self._on_progress(
                        completed + 1,
                        total_steps,
                        f"Wrote section {completed}/{n}: {sections[index].heading}",
                    )
            except Exception:
                # Don't keep paying for work whose result we'll discard.
                for pending in futures:
                    pending.cancel()
                raise

        stats.sections_wall_time = time.perf_counter() - wall_start
        stats.content_times = durations

        missing = [i for i, r in enumerate(results) if r is None]
        if missing:
            raise CompletionError(
                f"Section content missing for indices {missing}"
            )

        logger.info(
            f"Sections done in {stats.sections_wall_time:.1f}s "
            f"(sum of calls {sum(durations):.1f}s, "
            f"{stats.sections_speedup:.1f}x speedup)"
        )
        return [
            SectionContent(section=sections[i], content=results[i])  # type: ignore[arg-type]
            for i in range(n)
        ]

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
