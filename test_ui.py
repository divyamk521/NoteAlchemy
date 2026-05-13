import streamlit as st

from src.ui.styles import get_css
from src.ui.components import (
    render_sidebar,
    render_audio_input,
    render_youtube_input,
    render_text_input,
    render_welcome,
    render_notes,
)

from src.notes.models import (
    Section,
    NotesStructure,
    SectionContent,
    LectureNotes,
    GlossaryEntry,
)

from src.notes.generator import GenerationStats


# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------

st.set_page_config(
    page_title="NoteAlchemy",
    layout="wide",
)

# Inject CSS
st.markdown(get_css(), unsafe_allow_html=True)


# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------

options = render_sidebar()

st.write("Sidebar Options:", options)


# ---------------------------------------------------
# INPUT TESTING
# ---------------------------------------------------

mode = options["input_mode"]

if mode == "audio":
    uploaded = render_audio_input()

elif mode == "youtube":
    url = render_youtube_input()

elif mode == "text":
    transcript = render_text_input()


# ---------------------------------------------------
# FAKE NOTES OBJECT
# ---------------------------------------------------

structure = NotesStructure(
    title="Neural Networks",
    summary="Introduction to deep learning.",
    key_concepts=["ReLU", "Backpropagation"],
    sections=[
        Section(
            heading="Forward Propagation",
            sub_headings=["Activation Functions"]
        )
    ]
)

section_content = SectionContent(
    section=structure.sections[0],
    content="""
### Activation Functions

ReLU is widely used.

- Prevents vanishing gradients
- Used in CNNs

Function | Purpose
ReLU | Activation
Sigmoid | Probability
"""
)

notes = LectureNotes(
    structure=structure,
    sections=[section_content],
    glossary=[
        GlossaryEntry(
            term="ReLU",
            definition="Rectified Linear Unit activation."
        )
    ],
)

stats = GenerationStats(
    transcription_time=2.1,
    structure_time=4.2,
    generation_time=7.5,
    glossary_time=1.0,
    total_time=14.8,
)


# ---------------------------------------------------
# RENDER NOTES
# ---------------------------------------------------

st.divider()

render_notes(notes, stats)