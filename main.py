from config.settings import get_settings
from src.utils.logger import setup_logger
from src.llm.groq_clients import get_cached_client
from src.llm.completion import LLMClient
from src.notes.generator import NotesGenerator


# ---------------------------------------------------
# Setup
# ---------------------------------------------------

setup_logger()

settings = get_settings()

groq_client = get_cached_client(settings.groq_api_key)

llm = LLMClient(groq_client)


# ---------------------------------------------------
# Progress callback
# ---------------------------------------------------

def progress(step, total, message):
    print(f"\n[{step}/{total}] {message}")


# ---------------------------------------------------
# Generator
# ---------------------------------------------------

generator = NotesGenerator(
    llm=llm,
    generate_glossary=True,
    on_progress=progress,
)


# ---------------------------------------------------
# Fake transcript
# ---------------------------------------------------

transcript = """
Today we discussed neural networks and deep learning.

We explored neurons, activation functions,
forward propagation, backpropagation,
gradient descent, and optimization.

Neural networks learn patterns from data
by adjusting weights during training.
"""


# ---------------------------------------------------
# RUN PIPELINE
# ---------------------------------------------------

notes, stats = generator.generate(transcript)


# ---------------------------------------------------
# RESULTS
# ---------------------------------------------------

print("\n==============================")
print("FINAL RESULTS")
print("==============================\n")

print("TITLE:")
print(notes.title)

print("\nWORD COUNT:")
print(notes.word_count)

print("\nTOTAL TIME:")
print(stats.total_time)

print("\nAVG SECTION TIME:")
print(stats.avg_section_time)

print("\nTOTAL SECTIONS:")
print(stats.total_sections)

print("\n==============================")
print("MARKDOWN OUTPUT")
print("==============================\n")

print(notes.markdown[:5000])


# ---------------------------------------------------
# SAVE OUTPUT
# ---------------------------------------------------

with open("generated_notes.md", "w", encoding="utf-8") as f:
    f.write(notes.markdown)

print("\n✅ Notes saved to generated_notes.md")