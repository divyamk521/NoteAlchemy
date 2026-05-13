from config.settings import get_settings
from src.utils.logger import setup_logger

from groq_utils import (
    get_client,
    transcribe_audio,
    generate_structure,
    generate_section_content,
    assemble_notes,
)

# ---------------------------------------------------
# Setup
# ---------------------------------------------------

setup_logger()

settings = get_settings()

client = get_client(settings.groq_api_key)


# ---------------------------------------------------
# Fake Streamlit upload wrapper
# ---------------------------------------------------

class UploadedFile:
    def __init__(self, path):
        self.path = path
        self.name = path

    def read(self):
        with open(self.path, "rb") as f:
            return f.read()


audio = UploadedFile("test.mp4")


# ---------------------------------------------------
# STEP 1 — TRANSCRIPTION
# ---------------------------------------------------

print("\n==============================")
print("STEP 1 — TRANSCRIPTION")
print("==============================\n")

transcript = transcribe_audio(client, audio)

print(transcript[:1000])


# ---------------------------------------------------
# STEP 2 — STRUCTURE GENERATION
# ---------------------------------------------------

print("\n==============================")
print("STEP 2 — STRUCTURE")
print("==============================\n")

structure = generate_structure(client, transcript)

print(structure)


# ---------------------------------------------------
# STEP 3 — SECTION GENERATION
# ---------------------------------------------------

print("\n==============================")
print("STEP 3 — SECTION GENERATION")
print("==============================\n")

section_contents = []

for section in structure["sections"]:

    print(f"\nGenerating: {section['heading']}")

    content = generate_section_content(
        client,
        transcript,
        structure,
        section,
    )

    section_contents.append(content)

    print(content[:500])


# ---------------------------------------------------
# STEP 4 — FINAL NOTES
# ---------------------------------------------------

print("\n==============================")
print("STEP 4 — FINAL NOTES")
print("==============================\n")

notes = assemble_notes(structure, section_contents)

print(notes[:3000])


# ---------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------

with open("generated_notes.md", "w", encoding="utf-8") as f:
    f.write(notes)

print("\n✅ Notes saved to generated_notes.md")