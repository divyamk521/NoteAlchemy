# 🧙 NoteAlchemy

> AI-powered lecture notes — transcribe audio, generate structured notes instantly.

NoteAlchemy scaffolds the creation of structured lecture notes by iteratively
transcribing audio and generating content using **Groq's Whisper + Llama 3** APIs.
It strategically switches between **llama-3.3-70b-versatile** (quality, for outline) and
**llama-3.1-8b-instant** (speed, for section content) to balance quality and latency.

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🎧 Audio transcription | Whisper-large-v3 via Groq — MP3, WAV, M4A, FLAC, WEBM, OGG |
| ▶️ YouTube support | Download + transcribe directly from a YouTube URL via yt-dlp |
| 📝 Paste transcript | Skip transcription and generate notes from raw text |
| 🏗️ Scaffolded prompting | llama-3.3-70b-versatile → outline, llama-3.1-8b-instant → content (speed + quality) |
| 📖 Rich markdown | Tables, code blocks, blockquotes, headings, bullet points |
| 📚 Glossary | Auto-generated key-concept definitions |
| 📂 Export | Download as `.txt` or `.pdf` |
| 🌐 Language support | Auto-detect or specify: English, Spanish, French, German, Hindi… |
| 🔁 Retry logic | Exponential back-off on transient API errors |
| 🪵 Structured logging | loguru-based, rotated log files |

---

## 🗂️ Project Structure & Data Flow

```
NoteAlchemy/
│
├── main.py                         ← Streamlit entry point (thin orchestrator)
│
├── config/
│   ├── __init__.py
│   └── settings.py                 ← Pydantic-settings: all config from .env
│
├── src/
│   ├── __init__.py
│   │
│   ├── transcription/              ── LAYER 1: Audio → Text
│   │   ├── __init__.py
│   │   ├── whisper_client.py       ← Groq Whisper API wrapper
│   │   └── youtube_downloader.py  ← yt-dlp YouTube audio downloader
│   │
│   ├── llm/                        ── LAYER 2: LLM primitives
│   │   ├── __init__.py
│   │   ├── groq_client.py          ← Groq client factory & cache
│   │   ├── completion.py           ← Chat completion wrapper (text + JSON)
│   │   └── prompts.py              ← All system & user prompt templates
│   │
│   ├── notes/                      ── LAYER 3: Notes domain
│   │   ├── __init__.py
│   │   ├── models.py               ← Pydantic: Section, NotesStructure, LectureNotes
│   │   └── generator.py           ← Pipeline orchestrator (structure → content → glossary)
│   │
│   ├── export/                     ── LAYER 4: Output
│   │   ├── __init__.py
│   │   ├── text_exporter.py        ← Markdown → clean plain text
│   │   └── pdf_exporter.py        ← Markdown → styled PDF (fpdf2)
│   │
│   └── ui/                         ── LAYER 5: Streamlit UI
│       ├── __init__.py
│       ├── styles.py               ← All CSS in one place
│       └── components.py          ← Reusable render functions (sidebar, inputs, notes)
│       └── utils/
│           ├── __init__.py
│           ├── logger.py           ← loguru setup + get_logger()
│           ├── file_utils.py      ← Validation, temp files, path helpers
│           └── retry.py           ← Tenacity retry decorator
│
├── assets/
│   └── audio/                      ← Drop local audio files here for testing
│
├── examples/
│   ├── README.md
│   ├── essence_calculus/           ← Example: 3Blue1Brown — Essence of Calculus
│   └── transformers_explained/     ← Example: Google Cloud — Transformers Explained
│
├── logs/                           ← Auto-created; rotated log files
│
├── .streamlit/
│   └── config.toml                 ← Streamlit theme (dark academic)
│
├── .env.example                    ← Copy to .env and fill in your API key
├── .gitignore
└── requirements.txt
```

### Data Flow

```
USER INPUT
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  main.py  (Streamlit UI)                                │
│    ├── render_sidebar()   → user options                │
│    ├── render_*_input()   → audio / URL / text          │
│    └── "Generate" button                                │
└───────────────────────┬─────────────────────────────────┘
                        │
          ┌─────────────▼──────────────┐
          │  TRANSCRIPTION LAYER       │
          │  WhisperClient             │  ← Groq Whisper API
          │  YouTubeDownloader (yt-dlp)│  ← YouTube → M4A → Whisper
          └─────────────┬──────────────┘
                        │  transcript: str
          ┌─────────────▼──────────────┐
          │  NOTES GENERATOR           │
          │  NotesGenerator.generate() │
          │    │                       │
          │    ├─ _build_structure()   │  ← Llama 4 Maverick (quality)
          │    │    LLM JSON → Pydantic│
          │    │    NotesStructure     │
          │    │                       │
          │    ├─ _build_section_      │  ← Llama 4 Scout × N sections
          │    │   content() × N       │    (speed)
          │    │                       │
          │    └─ _build_glossary()    │  ← Llama 4 Scout (optional)
          │                            │
          │  returns: LectureNotes     │
          └─────────────┬──────────────┘
                        │
          ┌─────────────▼──────────────┐
          │  EXPORT LAYER              │
          │  TextExporter → .txt bytes │
          │  PDFExporter  → .pdf bytes │
          └─────────────┬──────────────┘
                        │
          ┌─────────────▼──────────────┐
          │  UI (render_notes)         │
          │  Notes tab · Transcript    │
          │  tab · JSON structure tab  │
          │  Download buttons          │
          └────────────────────────────┘
```

---

## 🚀 Quickstart (Local)

### Prerequisites

- Python **3.10+**
- A free **Groq API key** → [console.groq.com](https://console.groq.com)

> **Note on YouTube downloads:** yt-dlp is pure Python and downloads M4A
> audio natively without needing ffmpeg for most YouTube videos.
> If you encounter issues with specific videos, installing ffmpeg helps but is optional.

---

### Step 1 — Clone / extract the project

```bash
cd scribewizard
```

### Step 2 — Create a virtual environment

```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate.bat

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

All dependencies are pure Python — no C++ compilation required.

### Step 4 — Configure your API key

```bash
# Copy the template
cp .env.example .env

# Open .env in any editor and set your key:
# GROQ_API_KEY=gsk_your_key_here
```

Alternatively, you can paste the key directly in the app's sidebar — no `.env` needed.

### Step 5 — Run the app

```bash
python -m streamlit run main.py
```

Open **http://localhost:8501** in your browser.

---

## 🔧 Configuration

All settings live in `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Your Groq Cloud API key |
| `WHISPER_MODEL` | `whisper-large-v3` | Transcription model |
| `STRUCTURE_MODEL` | `meta-llama/llama-4-maverick-17b-128e-instruct` | Outline quality model |
| `CONTENT_MODEL` | `meta-llama/llama-4-scout-17b-16e-instruct` | Content speed model |
| `MAX_FILE_SIZE_MB` | `25` | Max audio upload size |
| `MAX_RETRIES` | `3` | API retry attempts |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## 📦 Dependencies

```
streamlit       — Web UI framework
groq            — Groq Cloud API (Whisper + Llama)
fpdf2           — Pure-Python PDF generation
yt-dlp          — YouTube audio download (pure Python)
pydantic        — Data validation & settings
pydantic-settings — .env loading
python-dotenv   — .env file support
tenacity        — Retry logic with exponential back-off
loguru          — Structured logging
rich            — Pretty terminal output
```

---

## ⚠️ Limitations

- Audio files must be under 25 MB (Groq limit).
- Generated notes may contain inaccuracies — verify important information.
- Very long lectures (>60 min) may need to be split.
- YouTube download requires a working internet connection and may fail for age-restricted or private videos.

---

## 🤝 Contributing

PRs are welcome! Please keep the separation of concerns:
- Prompt changes → `src/llm/prompts.py`
- UI changes → `src/ui/`
- New export formats → `src/export/`
- Config changes → `config/settings.py`

---

## 📄 Changelog

### v0.1.0
- Initial release
- Audio upload + YouTube URL + paste transcript inputs
- Whisper-large-v3 transcription
- Scaffolded Maverick (outline) + Scout (content) generation
- Glossary generation
- PDF + TXT export
- Modular architecture with separation of concerns
