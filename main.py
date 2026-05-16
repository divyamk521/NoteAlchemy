

import sys
import os

# Ensure project root is on sys.path so `src` and `config` are importable
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

from config.settings import get_settings
from src.utils.logger import setup_logger, get_logger
from src.ui import (
    get_css,
    render_sidebar,
    render_audio_input,
    render_youtube_input,
    render_text_input,
    render_notes,
    render_welcome,
    make_progress_callback,
)
from src.llm import build_client, GroqClientError, LLMClient
from src.transcription import WhisperClient, YouTubeDownloader
from src.notes import NotesGenerator
from src.utils import FileSizeError, UnsupportedFormatError

# ──────────────────────────────────────────────────────────────────────
#  One-time setup
# ──────────────────────────────────────────────────────────────────────

setup_logger()
logger = get_logger(__name__)
settings = get_settings()

st.set_page_config(
    page_title="ScribeWizard",
    page_icon="🧙",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(get_css(), unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────
#  Session-state defaults
# ──────────────────────────────────────────────────────────────────────

_DEFAULTS = {
    "api_key":          settings.groq_api_key,
    "transcript":       "",
    "notes":            None,   # LectureNotes | None
    "stats":            None,   # GenerationStats | None
    "generation_done":  False,
    "error_message":    "",
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ──────────────────────────────────────────────────────────────────────
#  Sidebar
# ──────────────────────────────────────────────────────────────────────

opts = render_sidebar()

# ──────────────────────────────────────────────────────────────────────
#  Header
# ──────────────────────────────────────────────────────────────────────

st.markdown("# 🧙 ScribeWizard")
st.markdown(
    "<p style='color:#6a6258;margin-top:-0.8rem;"
    "font-family:JetBrains Mono,monospace;font-size:0.82rem;'>"
    "Transform lectures into structured notes — powered by Groq.</p>",
    unsafe_allow_html=True,
)
st.divider()

# ──────────────────────────────────────────────────────────────────────
#  Step 1 — Input
# ──────────────────────────────────────────────────────────────────────

input_col, hint_col = st.columns([3, 1])

with input_col:
    st.markdown("### Step 1 — Provide Lecture Content")
    uploaded_file = None
    youtube_url   = None
    pasted_text   = None

    if opts["input_mode"] == "audio":
        uploaded_file = render_audio_input()
    elif opts["input_mode"] == "youtube":
        youtube_url = render_youtube_input()
    else:
        pasted_text = render_text_input()

with hint_col:
    st.markdown("&nbsp;")
    with st.expander("💡 Tips"):
        st.markdown(
            "- Clear audio with little background noise works best.\n"
            "- Lectures under ~60 min are ideal.\n"
            "- YouTube auto-captions also work — paste as transcript.\n"
            "- yt-dlp downloads audio directly from YouTube links."
        )
    with st.expander("📁 Supported formats"):
        st.markdown("MP3 · MP4 · WAV · FLAC · M4A · WEBM · OGG (max 25 MB)")

# ──────────────────────────────────────────────────────────────────────
#  Step 2 — Generate
# ──────────────────────────────────────────────────────────────────────

st.markdown("### Step 2 — Generate Notes")
generate_btn = st.button("✨ Generate Notes", type="primary")

if generate_btn:
    # Reset previous run
    st.session_state["generation_done"] = False
    st.session_state["notes"]           = None
    st.session_state["stats"]           = None
    st.session_state["error_message"]   = ""

    # ── Validate API key ──────────────────────────────────────────────
    if not opts["api_key"]:
        st.error("❌ Please enter your Groq API key in the sidebar.")
        st.stop()

    # ── Build Groq client ─────────────────────────────────────────────
    try:
        groq_client = build_client(opts["api_key"])
    except GroqClientError as exc:
        st.error(f"❌ {exc}")
        st.stop()

    whisper = WhisperClient(groq_client)
    llm     = LLMClient(groq_client)

    progress_bar = st.progress(0, text="Starting…")
    status_text  = st.empty()

    try:
        # ── Transcription ─────────────────────────────────────────────
        transcript: str = ""

        if opts["input_mode"] == "audio" and uploaded_file is not None:
            status_text.info("🎙️ Transcribing audio with Whisper-large-v3…")
            progress_bar.progress(5, text="Transcribing audio…")
            uploaded_file.seek(0)
            result = whisper.transcribe_upload(
                file_bytes=uploaded_file.read(),
                filename=uploaded_file.name,
                language=opts["language"],
            )
            transcript = result.text
            logger.info(f"Transcription complete: {result.word_count} words")

        elif opts["input_mode"] == "youtube" and youtube_url:
            status_text.info("⬇️ Downloading YouTube audio…")
            progress_bar.progress(5, text="Downloading audio…")
            downloader = YouTubeDownloader()
            with downloader.download(youtube_url) as dl_result:
                st.session_state["_yt_title"] = dl_result.title
                status_text.info(
                    f"🎙️ Transcribing '{dl_result.title}' ({dl_result.duration_seconds}s)…"
                )
                progress_bar.progress(15, text="Transcribing…")
                result = whisper.transcribe_file(
                    dl_result.path,
                    language=opts["language"],
                )
                transcript = result.text

        elif opts["input_mode"] == "text" and pasted_text:
            transcript = pasted_text
            progress_bar.progress(10, text="Transcript ready")

        else:
            st.error("❌ Please provide audio, a YouTube URL, or a transcript.")
            st.stop()

        if not transcript.strip():
            st.error("❌ Transcript is empty — nothing to generate notes from.")
            st.stop()

        st.session_state["transcript"] = transcript

        # ── Notes generation ──────────────────────────────────────────
        progress_bar.progress(20, text="Generating notes…")

        callback = make_progress_callback(progress_bar, status_text)

        # Offset progress by 20 (transcription used 0-20)
        def offset_callback(current, total, message):
            pct = 20 + int(75 * current / max(total, 1))
            progress_bar.progress(pct, text=message)
            status_text.info(f"⚙️ {message}")

        generator = NotesGenerator(
            llm=llm,
            generate_glossary=opts["generate_glossary"],
            on_progress=offset_callback,
        )
        notes, stats = generator.generate(transcript)

        st.session_state["notes"]          = notes
        st.session_state["stats"]          = stats
        st.session_state["generation_done"] = True

        progress_bar.progress(100, text="Done!")
        status_text.success(
            f"✅ Notes generated in {stats.total_time:.1f}s — "
            f"{notes.word_count:,} words across {len(notes.sections)} sections."
        )
        logger.success("Pipeline complete.")

    except (FileSizeError, UnsupportedFormatError) as exc:
        st.error(f"❌ File error: {exc}")
        logger.warning(str(exc))
    except GroqClientError as exc:
        st.error(f"❌ Groq error: {exc}")
        logger.error(str(exc))
    except Exception as exc:
        st.error(f"❌ Unexpected error: {exc}")
        logger.exception("Unexpected pipeline error")



if st.session_state["generation_done"] and st.session_state["notes"]:
    st.divider()
    render_notes(st.session_state["notes"], st.session_state["stats"])

elif not st.session_state["generation_done"]:
    st.divider()
    render_welcome()
