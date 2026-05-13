"""
src/ui/styles.py
-----------------
All custom CSS for the Streamlit app, injected once at startup via
``st.markdown(get_css(), unsafe_allow_html=True)``.

Keeping styles here avoids cluttering main.py and makes theming easy.
"""

GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Lora:ital,wght@0,400;0,600;1,400&"
    "family=JetBrains+Mono:wght@400;600&"
    "family=Playfair+Display:wght@700;900&"
    "display=swap"
)


def get_css() -> str:
    return f"""
<style>
@import url('{GOOGLE_FONTS_URL}');

/* ── Base ───────────────────────────────────────────────────────── */
html, body, [class*="css"] {{
    font-family: 'Lora', Georgia, serif;
}}
.stApp {{
    background: #13120f;
    color: #e8e0d0;
}}

/* ── Sidebar ────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: #0e0d0b;
    border-right: 1px solid #2a2825;
}}
section[data-testid="stSidebar"] .stMarkdown p {{
    color: #9a8f7e;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
}}

/* ── Headings ───────────────────────────────────────────────────── */
h1 {{
    font-family: 'Playfair Display', Georgia, serif;
    color: #f0e6cc;
    font-size: 2.2rem;
    letter-spacing: -0.03em;
}}
h2, h3 {{
    font-family: 'Lora', Georgia, serif;
    color: #f0e6cc;
    letter-spacing: -0.02em;
}}

/* ── Buttons ────────────────────────────────────────────────────── */
.stButton > button {{
    background: #c9933a;
    color: #0f0e0d;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    border: none;
    border-radius: 4px;
    padding: 0.6rem 1.6rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    transition: background 0.18s, transform 0.1s;
}}
.stButton > button:hover {{
    background: #e0a84a;
    transform: translateY(-1px);
}}
.stButton > button:active {{
    transform: translateY(0);
}}

/* ── Download buttons ───────────────────────────────────────────── */
.stDownloadButton > button {{
    background: transparent;
    color: #c9933a;
    border: 1px solid #c9933a44;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.76rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    border-radius: 3px;
    padding: 0.35rem 0.9rem;
    transition: all 0.18s;
}}
.stDownloadButton > button:hover {{
    background: #c9933a18;
    border-color: #c9933a;
}}

/* ── Progress ───────────────────────────────────────────────────── */
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, #c9933a, #e0a84a);
}}

/* ── Inputs ─────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {{
    background: #1a1815;
    color: #e8e0d0;
    border: 1px solid #2e2b27;
    border-radius: 4px;
    font-family: 'Lora', serif;
    font-size: 0.93rem;
}}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {{
    border-color: #c9933a55;
    box-shadow: 0 0 0 2px #c9933a22;
}}

/* ── File uploader ──────────────────────────────────────────────── */
[data-testid="stFileUploader"] {{
    background: #1a1815;
    border: 1.5px dashed #3a3630;
    border-radius: 8px;
    transition: border-color 0.2s;
}}
[data-testid="stFileUploader"]:hover {{
    border-color: #c9933a66;
}}

/* ── Tabs ───────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {{
    background: transparent;
    border-bottom: 1px solid #2e2b27;
    gap: 0;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #6a6258;
    padding: 0.5rem 1.2rem;
    background: transparent;
    border: none;
}}
.stTabs [aria-selected="true"] {{
    color: #c9933a;
    border-bottom: 2px solid #c9933a;
    background: transparent;
}}

/* ── Expander ───────────────────────────────────────────────────── */
.streamlit-expanderHeader {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #6a6258;
    letter-spacing: 0.05em;
}}

/* ── Alerts ─────────────────────────────────────────────────────── */
.stAlert {{
    background: #1a1815;
    border-radius: 5px;
}}

/* ── Notes container ────────────────────────────────────────────── */
.notes-container {{
    background: #1a1815;
    border: 1px solid #2e2b27;
    border-radius: 8px;
    padding: 2.2rem 2.8rem;
    line-height: 1.8;
    color: #ddd5c0;
    font-size: 0.96rem;
}}
.notes-container h1 {{
    font-size: 1.7rem;
    border-bottom: 1px solid #3a3630;
    padding-bottom: 0.5rem;
    margin-bottom: 1.2rem;
}}
.notes-container h2 {{
    font-size: 1.25rem;
    color: #e8d8a8;
    margin-top: 2rem;
    margin-bottom: 0.6rem;
}}
.notes-container h3 {{
    font-size: 1.05rem;
    color: #c9b898;
    margin-top: 1.2rem;
}}
.notes-container code {{
    font-family: 'JetBrains Mono', monospace;
    background: #0f0e0d;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.82em;
    color: #d4a84e;
}}
.notes-container pre code {{
    display: block;
    padding: 1rem 1.2rem;
    overflow-x: auto;
    line-height: 1.6;
    border-left: 3px solid #c9933a;
    border-radius: 0 4px 4px 0;
}}
.notes-container blockquote {{
    border-left: 3px solid #c9933a;
    padding-left: 1rem;
    color: #9a8f7e;
    font-style: italic;
    margin: 1rem 0;
}}
.notes-container table {{
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
    font-size: 0.88rem;
}}
.notes-container th {{
    background: #242118;
    color: #c9933a;
    padding: 0.5rem 0.8rem;
    border: 1px solid #3a3630;
    text-align: left;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}
.notes-container td {{
    padding: 0.45rem 0.8rem;
    border: 1px solid #2e2b27;
    vertical-align: top;
}}
.notes-container tr:nth-child(even) td {{
    background: #161410;
}}

/* ── Stats bar ──────────────────────────────────────────────────── */
.stats-bar {{
    display: flex;
    gap: 2rem;
    padding: 0.8rem 1.2rem;
    background: #1a1815;
    border: 1px solid #2e2b27;
    border-radius: 6px;
    margin-bottom: 1.2rem;
}}
.stat-item {{
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
}}
.stat-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.68rem;
    color: #6a6258;
    text-transform: uppercase;
    letter-spacing: 0.07em;
}}
.stat-value {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 600;
    color: #c9933a;
}}

/* ── Welcome placeholder ────────────────────────────────────────── */
.welcome-placeholder {{
    text-align: center;
    padding: 4rem 2rem;
    color: #4a4540;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    line-height: 2;
}}
.welcome-icon {{
    font-size: 3.5rem;
    margin-bottom: 1rem;
    display: block;
}}
</style>
"""
