import os
import tempfile
from groq import Groq

STRUCTURE_MODEL = "llama-3.3-70b-versatile" 
CONTENT_MODEL   = "llama-3.1-8b-instant"   

def get_client(api_key: str) -> Groq:
    """Return an authenticated Groq client."""
    return Groq(api_key=api_key)

def transcribe_audio(client: Groq, audio_file) -> str:
    """
    Transcribe an uploaded audio file using Whisper-large on Groq.
    """
    # Write to a temporary file so the Groq SDK can read it
    suffix = os.path.splitext(audio_file.name)[-1] or ".mp3"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_file.read())
        tmp_path = tmp.name

    try:
        with open(tmp_path, "rb") as f:
            response = client.audio.transcriptions.create(
                file=(audio_file.name, f),
                model="whisper-large-v3",
                response_format="text",
            )
        return response  # returns plain string when response_format="text"
    finally:
        os.unlink(tmp_path)#after everything i am deleting the temp file

STRUCTURE_SYSTEM = """You are an expert academic note-taker and educator.
Your task is to analyse a lecture transcript and produce a **detailed outline** for structured lecture notes.

Return ONLY a JSON object in this exact format (no markdown fences, no extra keys):
{
  "title": "<concise lecture title>",
  "sections": [
    {
      "heading": "<section heading>",
      "sub_headings": ["<sub-heading 1>", "<sub-heading 2>"]
    }
  ]
}

Guidelines:
- Create 4–8 top-level sections that cover the full lecture.
- Each section should have 2–5 sub-headings.
- Headings should be descriptive and informative, not generic.
- Order sections to match the logical flow of the lecture."""

def generate_structure(client: Groq, transcript: str) -> dict:
   
    import json

    response = client.chat.completions.create(
        model=STRUCTURE_MODEL,
        messages=[
            {"role": "system", "content": STRUCTURE_SYSTEM},
            {"role": "user",   "content": f"Lecture transcript:\n\n{transcript}"},
        ],
        temperature=0.3,
        max_tokens=1500,
    )

    raw = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    return json.loads(raw)

CONTENT_SYSTEM = """You are an expert academic note-taker producing detailed, well-structured lecture notes.

You will be given:
1. The full lecture transcript
2. The overall notes structure (title + all section headings)
3. The specific section and sub-headings you must write now

Write comprehensive notes for ONLY the assigned section. Use markdown:
- Use **bold** for key terms/concepts on first introduction
- Use bullet points and numbered lists where appropriate
- Include tables when comparing concepts or listing properties
- Include code blocks (```language ... ```) for any code or pseudocode
- Be thorough — a student should not need to re-read the transcript

Do NOT include the section heading itself (it will be added automatically).
Do NOT write notes for other sections."""

def generate_section_content(
    client: Groq,
    transcript: str,
    structure: dict,
    section: dict,
) -> str:
    
    import json

    structure_summary = f"Title: {structure['title']}\nSections:\n"
    for s in structure["sections"]:
        structure_summary += f"  - {s['heading']}\n"
        for sh in s.get("sub_headings", []):
            structure_summary += f"      • {sh}\n"

    section_desc = f"Section: {section['heading']}\nSub-headings to cover:\n"
    for sh in section.get("sub_headings", []):
        section_desc += f"  - {sh}\n"

    user_msg = (
        f"TRANSCRIPT:\n{transcript}\n\n"
        f"FULL STRUCTURE:\n{structure_summary}\n\n"
        f"YOUR ASSIGNED SECTION:\n{section_desc}"
    )

    response = client.chat.completions.create(
        model=CONTENT_MODEL,
        messages=[
            {"role": "system", "content": CONTENT_SYSTEM},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.4,
        max_tokens=2000,
    )

    return response.choices[0].message.content.strip()

def assemble_notes(structure: dict, section_contents: list[str]) -> str:
   
    lines = [f"# {structure['title']}\n"]

    for section, content in zip(structure["sections"], section_contents):
        lines.append(f"## {section['heading']}\n")

        
        sub_headings = section.get("sub_headings", [])
       
        lines.append(content)
        lines.append("")  # blank line between sections

    return "\n".join(lines)
