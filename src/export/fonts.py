"""Unicode font resolution and text sanitising for PDF export.

fpdf2's built-in "core" fonts (Helvetica, Courier) are limited to
latin-1. Any character outside that range raises
``FPDFUnicodeEncodingException`` — and LLM prose is full of them: em
dashes, curly quotes, arrows, bullets. Export crashed on ordinary
English output, never mind other languages.

We bundle DejaVu Sans, which covers Latin, Latin Extended, Greek,
Cyrillic and the typographic punctuation that was breaking exports.

DejaVu does *not* cover Devanagari or CJK. Rather than crash on Hindi or
Chinese notes, :func:`sanitize_for_font` replaces unrepresentable
characters. Rendering those scripts properly needs a Noto CJK /
Devanagari face, which is ~10x the size — tracked as future work.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import NamedTuple, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)

#: Bundled font directory: <repo>/assets/fonts
FONT_DIR = Path(__file__).resolve().parents[2] / "assets" / "fonts"

#: Typographic characters mapped to ASCII, used when no Unicode font is
#: available. Keeps output readable instead of littered with "?".
_TRANSLITERATIONS = {
    "—": "-",   # em dash
    "–": "-",   # en dash
    "−": "-",   # minus sign
    "‘": "'",   # left single quote
    "’": "'",   # right single quote
    "‚": ",",
    "“": '"',   # left double quote
    "”": '"',   # right double quote
    "…": "...",  # ellipsis
    "•": "-",   # bullet
    "·": "-",   # middle dot
    "→": "->",
    "←": "<-",
    "↔": "<->",
    "⇒": "=>",
    "≤": "<=",
    "≥": ">=",
    "≠": "!=",
    "×": "x",
    "÷": "/",
    " ": " ",   # non-breaking space
    "​": "",    # zero-width space
    "′": "'",
    "″": '"',
}


class FontSet(NamedTuple):
    """A resolved family of faces, or the core-font fallback."""

    family: str
    mono_family: str
    #: (style, path) pairs to register via ``FPDF.add_font``
    faces: tuple[tuple[str, Path], ...]
    #: True when the family covers more than latin-1
    unicode: bool


#: Regular / Bold / Italic / BoldItalic + monospace, as fpdf style codes.
_DEJAVU_FACES = (
    ("", "DejaVuSans.ttf"),
    ("B", "DejaVuSans-Bold.ttf"),
    ("I", "DejaVuSans-Oblique.ttf"),
    ("BI", "DejaVuSans-BoldOblique.ttf"),
)
_DEJAVU_MONO = "DejaVuSansMono.ttf"

_CORE_FALLBACK = FontSet(
    family="Helvetica",
    mono_family="Courier",
    faces=(),
    unicode=False,
)


@lru_cache(maxsize=1)
def resolve_font_set() -> FontSet:
    """Return the best available :class:`FontSet`.

    Prefers the bundled DejaVu faces. Falls back to fpdf2's core fonts
    when they are missing, in which case callers must pass text through
    :func:`sanitize_for_font` to avoid an encoding exception.
    """
    required = [FONT_DIR / name for _, name in _DEJAVU_FACES]
    mono = FONT_DIR / _DEJAVU_MONO

    missing = [p.name for p in [*required, mono] if not p.is_file()]
    if missing:
        logger.warning(
            f"Unicode fonts missing from {FONT_DIR} ({', '.join(missing)}). "
            "Falling back to core fonts; non-latin-1 characters will be "
            "transliterated or dropped."
        )
        return _CORE_FALLBACK

    faces = tuple(
        (style, FONT_DIR / name) for style, name in _DEJAVU_FACES
    ) + (("", mono),)
    logger.debug(f"Using bundled DejaVu Unicode fonts from {FONT_DIR}")
    return FontSet(
        family="DejaVuSans",
        mono_family="DejaVuSansMono",
        faces=faces,
        unicode=True,
    )


def sanitize_for_font(text: str, font_set: Optional[FontSet] = None) -> str:
    """Make *text* safe to render with *font_set*.

    With a Unicode font, only characters outside the font's own coverage
    (Devanagari, CJK) are transliterated or dropped. With core fonts,
    everything outside latin-1 is.

    Never raises — the whole point is that PDF export cannot fail on
    unexpected input.
    """
    fs = font_set or resolve_font_set()

    out: list[str] = []
    for ch in text:
        if _representable(ch, fs):
            out.append(ch)
            continue
        replacement = _TRANSLITERATIONS.get(ch)
        if replacement is not None:
            out.append(replacement)
        elif ch.isspace():
            out.append(" ")
        else:
            # Unrepresentable and no sensible ASCII equivalent.
            out.append("?")
    return "".join(out)


def _representable(ch: str, fs: FontSet) -> bool:
    if not fs.unicode:
        return ord(ch) < 256
    # DejaVu covers Latin/Greek/Cyrillic and general punctuation. Treat
    # the Indic, CJK and other unsupported blocks as out of range.
    cp = ord(ch)
    if cp < 0x0250:          # Latin + Latin Extended-A/B
        return True
    if 0x0370 <= cp <= 0x04FF:  # Greek + Cyrillic
        return True
    if 0x2000 <= cp <= 0x22FF:  # punctuation, symbols, arrows, maths
        return True
    if cp < 0x0300:
        return True
    return False
