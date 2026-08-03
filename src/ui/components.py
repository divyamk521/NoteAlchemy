"""
src/ui/components.py
---------------------
Reusable Streamlit UI component functions.

Each function renders one logical section of the UI and returns
any user-input values needed by the caller.
"""

from __future__ import annotations

from typing import Optional
import streamlit as st

from config.settings import get_settings
from src.notes.models import LectureNotes
from src.notes.generator import GenerationStats
from src.export import TextExporter, PDFExporter

settings = get_settings()
_text_exporter = TextExporter()
_pdf_exporter  = PDFExporter()


# ──────────────────────────────────────────────────────────────────────
#  Sidebar
# ──────────────────────────────────────────────────────────────────────

def render_sidebar() -> dict:
    """
    Render the sidebar and return a dict of user-configured options:

    Returns
    -------
    dict with keys:
        api_key          : str
        input_mode       : "audio" | "youtube" | "text"
        generate_glossary: bool
        language         : str | None
    """
    with st.sidebar:
        st.markdown("## 🧙 NoteAlchemy")
        st.markdown(
            "<p style='color:#6a6258;font-size:0.78rem;"
            "font-family:JetBrains Mono,monospace;margin-top:-0.5rem;'>"
            "AI lecture notes generator</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        # API key
        api_key = st.text_input(
            "Groq API Key",
            value=st.session_state.get("api_key", settings.groq_api_key),
            type="password",
            help="Get a free key at console.groq.com",
            placeholder="gsk_…",
        )
        if api_key:
            st.session_state["api_key"] = api_key

        st.divider()

        # Input mode
        st.markdown(
            "<p style='color:#9a8f7e;font-size:0.72rem;"
            "font-family:JetBrains Mono,monospace;letter-spacing:0.06em;"
            "text-transform:uppercase;'>INPUT MODE</p>",
            unsafe_allow_html=True,
        )
        mode_label = st.radio(
            "Input mode",
            ["🎧 Audio Upload", "▶️ YouTube URL", "📝 Paste Transcript"],
            label_visibility="collapsed",
        )
        mode_map = {
            "🎧 Audio Upload": "audio",
            "▶️ YouTube URL": "youtube",
            "📝 Paste Transcript": "text",
        }
        input_mode = mode_map[mode_label]

        st.divider()

        # Generation options
        st.markdown(
            "<p style='color:#9a8f7e;font-size:0.72rem;"
            "font-family:JetBrains Mono,monospace;letter-spacing:0.06em;"
            "text-transform:uppercase;'>OPTIONS</p>",
            unsafe_allow_html=True,
        )
        generate_glossary = st.toggle("Generate Glossary", value=True)
        language = st.selectbox(
            "Transcript language",
            ["Auto-detect", "English", "Spanish", "French", "German",
             "Hindi", "Portuguese", "Italian", "Japanese", "Chinese"],
            index=0,
        )
        lang_map = {
            "Auto-detect": None, "English": "en", "Spanish": "es",
            "French": "fr", "German": "de", "Hindi": "hi",
            "Portuguese": "pt", "Italian": "it", "Japanese": "ja",
            "Chinese": "zh",
        }

        st.divider()

        # Model info
        st.markdown(
            "<p style='color:#9a8f7e;font-size:0.72rem;"
            "font-family:JetBrains Mono,monospace;letter-spacing:0.06em;"
            "text-transform:uppercase;'>MODELS</p>",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;"
            f"color:#6a6258;line-height:1.9'>"
            f"🎙️ <span style='color:#c9933a'>{settings.whisper_model}</span><br>"
            f"🏗️ <span style='color:#c9933a'>{settings.structure_model.split('/')[-1]}</span><br>"
            f"✍️ <span style='color:#c9933a'>{settings.content_model.split('/')[-1]}</span>"
            f"</div>",
            unsafe_allow_html=True,
        )

        st.divider()
        st.markdown(
            "<p style='color:#3a3530;font-size:0.68rem;"
            "font-family:JetBrains Mono,monospace;'>v0.1.0 · Beta · "
            "Content may be inaccurate.</p>",
            unsafe_allow_html=True,
        )

    return {
        "api_key": st.session_state.get("api_key", ""),
        "input_mode": input_mode,
        "generate_glossary": generate_glossary,
        "language": lang_map.get(language),
    }


# ──────────────────────────────────────────────────────────────────────
#  Input panels
# ──────────────────────────────────────────────────────────────────────

def render_audio_input():
    """Return (uploaded_file | None)."""
    st.markdown("#### Upload Audio File")
    uploaded = st.file_uploader(
        "Drop an audio file here",
        type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm", "ogg", "flac"],
        label_visibility="collapsed",
    )
    if uploaded:
        st.audio(uploaded)
        size_mb = len(uploaded.getvalue()) / (1024 * 1024)
        st.caption(f"📁 {uploaded.name} · {size_mb:.1f} MB")
    return uploaded


def render_youtube_input() -> Optional[str]:
    """Return a YouTube URL string or None."""
    st.markdown("#### YouTube URL")
    url = st.text_input(
        "Paste a YouTube link",
        placeholder="https://www.youtube.com/watch?v=…",
        label_visibility="collapsed",
    )
    if url:
        from src.transcription import YouTubeDownloader
        if not YouTubeDownloader.is_valid_youtube_url(url):
            st.warning("That doesn't look like a valid YouTube URL.")
            return None
        st.caption(f"🔗 {url}")
    return url or None


def render_text_input() -> Optional[str]:
    """Return pasted transcript text or None."""
    st.markdown("#### Paste Transcript")
    text = st.text_area(
        "Paste your lecture transcript",
        height=220,
        placeholder="Paste transcript here…",
        label_visibility="collapsed",
    )
    if text.strip():
        word_count = len(text.split())
        st.caption(f"📝 {word_count:,} words pasted")
        return text.strip()
    return None


# ──────────────────────────────────────────────────────────────────────
#  Progress display
# ──────────────────────────────────────────────────────────────────────

def make_progress_callback(progress_bar, status_text):
    """
    Factory: returns a ProgressCallback that updates Streamlit widgets.
    """
    def callback(current: int, total: int, message: str) -> None:
        pct = int(100 * current / max(total, 1))
        progress_bar.progress(pct, text=message)
        status_text.info(f"⚙️ {message}")
    return callback


# ──────────────────────────────────────────────────────────────────────
#  Notes display
# ──────────────────────────────────────────────────────────────────────

def render_stats_bar(notes: LectureNotes, stats: GenerationStats) -> None:
    """Render a compact statistics bar above the notes."""
    st.markdown(
        f"""
        <div class="stats-bar">
            <div class="stat-item">
                <span class="stat-label">Sections</span>
                <span class="stat-value">{len(notes.sections)}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Words</span>
                <span class="stat-value">{notes.word_count:,}</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Generated in</span>
                <span class="stat-value">{stats.total_time:.1f}s</span>
            </div>
            <div class="stat-item">
                <span class="stat-label">Glossary terms</span>
                <span class="stat-value">{len(notes.glossary)}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_download_buttons(notes: LectureNotes) -> None:
    """Render the .txt and .pdf download buttons side by side."""
    col1, col2, _ = st.columns([1, 1, 5])
    with col1:
        st.download_button(
            label="⬇ .txt",
            data=_text_exporter.export(notes),
            file_name=_text_exporter.filename(notes),
            mime="text/plain",
        )
    with col2:
        st.download_button(
            label="⬇ .pdf",
            data=_pdf_exporter.export(notes),
            file_name=_pdf_exporter.filename(notes),
            mime="application/pdf",
        )


def render_notes(notes: LectureNotes, stats: GenerationStats) -> None:
    """Render the complete notes section: stats, tabs, download buttons."""
    st.markdown("### 📖 Your Notes")
    render_stats_bar(notes, stats)
    render_download_buttons(notes)

    tab_notes, tab_transcript, tab_structure = st.tabs(
        ["NOTES", "TRANSCRIPT", "JSON STRUCTURE"]
    )

    with tab_notes:
        # Render as markdown, NOT as raw HTML. notes.markdown is model
        # output derived from user-supplied transcript text, so
        # interpolating it into a <div> with unsafe_allow_html=True let a
        # crafted transcript inject script or event-handler attributes —
        # a stored-XSS vector as soon as notes are shared between users.
        # Passing it to st.markdown() also means headings, tables and
        # code fences are parsed properly instead of the first line being
        # swallowed as an HTML block.
        with st.container(key="notes_container"):
            st.markdown(notes.markdown)

    with tab_transcript:
        transcript = st.session_state.get("transcript", "")
        if transcript:
            word_count = len(transcript.split())
            st.caption(f"Transcript — {word_count:,} words")
            st.text_area(
                "Transcript",
                value=transcript,
                height=400,
                label_visibility="collapsed",
            )
        else:
            st.info("Transcript not available.")

    with tab_structure:
        import json
        st.json(notes.structure.model_dump())


# ──────────────────────────────────────────────────────────────────────
#  Welcome placeholder
# ──────────────────────────────────────────────────────────────────────

def render_welcome() -> None:
    st.markdown(
        """
        <div class="welcome-placeholder">
            <span class="welcome-icon">🧙</span>
            Upload audio, paste a YouTube link, or drop in a transcript.<br>
            Hit <strong style="color:#c9933a;">Generate Notes</strong> and NoteAlchemy
            will transcribe, structure, and write<br>
            comprehensive lecture notes — automatically.
        </div>
        """,
        unsafe_allow_html=True,
    )
