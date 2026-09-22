"""
app.py — MathMate v4.0 Multimodal Streamlit UI
Two-mode: TEACH (Socratic) / DIRECT (full solution)
Multi-subject: Mathematics · Physics · Chemistry
CBSE NCERT Class 10
"""

import os, tempfile, re
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from build_index import build_faiss_from_pdf, is_index_built
from mathmate import MathMate, SUBJECTS
from multimodal import voice_to_text, image_to_description, detect_image_type, mime_from_filename
import fitz  # PyMuPDF — for worksheet PDF extraction

st.set_page_config(
    page_title="MathMate v4.0 — NCERT Tutor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,500;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

:root {
  --paper: #FAF7F0;
  --ink: #23262B;
  --rule-blue: #2B4C7E;
  --pencil: #6B6558;
  --correct: #3F7D4F;
  --flag: #B54834;
  --margin-red: #D05A4F;
  --desk-bg: #EFECE6;
  --card-bg: #F4F0E8;
  --shadow-subtle: 0 2px 8px rgba(35, 38, 43, 0.05);
}

@media (prefers-color-scheme: dark) {
  :root {
    --paper: #1C2320;
    --ink: #EDE7D9;
    --rule-blue: #4A72A8;
    --pencil: #A8A294;
    --correct: #6FB080;
    --flag: #D97362;
    --margin-red: #C85A4F;
    --desk-bg: #141A17;
    --card-bg: #232C28;
    --shadow-subtle: 0 2px 8px rgba(0, 0, 0, 0.2);
  }
}

html, body, [class*="css"] {
  font-family: 'IBM Plex Sans', sans-serif !important;
  color: var(--ink) !important;
}

h1, h2, h3, h4, .serif-font {
  font-family: 'Lora', serif !important;
}

#MainMenu, footer { visibility: hidden; }

/* Main app background: notebook ruling pattern */
.stApp {
  background-color: var(--paper) !important;
  background-image: repeating-linear-gradient(
    0deg,
    transparent,
    transparent 27px,
    rgba(43, 76, 126, 0.05) 27px,
    rgba(43, 76, 126, 0.05) 28px
  ) !important;
  color: var(--ink) !important;
}

/* Sidebar: Study Desk Vernacular */
[data-testid="stSidebar"] {
  background-color: var(--desk-bg) !important;
  border-right: 2px solid rgba(43, 76, 126, 0.12) !important;
}

[data-testid="stSidebar"] * {
  color: var(--ink) !important;
}

/* Sidebar desk sections */
.desk-section-header {
  font-family: 'Lora', serif;
  font-size: 14px;
  font-weight: 600;
  color: var(--rule-blue);
  border-bottom: 1px solid rgba(43, 76, 126, 0.15);
  padding-bottom: 4px;
  margin-bottom: 12px;
}

/* Knowledge base cards in sidebar */
.desk-kb-card {
  background: var(--card-bg);
  border: 1px solid rgba(35, 38, 43, 0.1);
  border-left: 4px solid var(--rule-blue);
  border-radius: 6px;
  padding: 8px 12px;
  margin-bottom: 8px;
  font-size: 13px;
  box-shadow: var(--shadow-subtle);
}

.desk-kb-card.idx-ready {
  border-left-color: var(--correct);
}

.desk-kb-card.idx-missing {
  border-left-color: var(--pencil);
  opacity: 0.7;
}

/* Mode Indicator */
.desk-mode-box {
  background: var(--card-bg);
  border: 1px solid rgba(43, 76, 126, 0.2);
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 500;
  box-shadow: var(--shadow-subtle);
  margin-top: 8px;
}

.desk-mode-box.teach {
  border-left: 4px solid var(--rule-blue);
}

.desk-mode-box.direct {
  border-left: 4px solid #D97706;
}

/* Messages Area with Red Notebook Margin Line */
[data-testid="stChatMessage"] {
  background: transparent !important;
  border: none !important;
  border-left: 2px solid var(--margin-red) !important;
  border-radius: 0 !important;
  padding-left: 18px !important;
  margin-bottom: 24px !important;
  box-shadow: none !important;
}

[data-testid="stChatMessage"] p {
  font-size: 15px !important;
  line-height: 1.85 !important;
  color: var(--ink) !important;
}

[data-testid="stChatMessage"] strong {
  color: var(--ink) !important;
  font-weight: 600;
}

/* Code & Math Monospace */
[data-testid="stChatMessage"] code, .mono-font {
  font-family: 'IBM Plex Mono', monospace !important;
  font-size: 13.5px !important;
  background: rgba(43, 76, 126, 0.07) !important;
  color: var(--rule-blue) !important;
  padding: 2px 6px !important;
  border-radius: 4px !important;
}

/* Equation block ($$...$$) styled like notebook boxed calculation */
.eq-block {
  background: rgba(43, 76, 126, 0.04);
  border-left: 3px solid var(--rule-blue);
  border-radius: 0 6px 6px 0;
  padding: 14px 20px;
  margin: 14px 0;
  overflow-x: auto;
  font-family: 'IBM Plex Mono', monospace;
}

/* DIRECT mode final boxed answer animation */
.direct-answer-box {
  border: 2px solid var(--rule-blue);
  border-radius: 8px;
  padding: 12px 18px;
  background: rgba(43, 76, 126, 0.05);
  display: inline-block;
  margin: 10px 0;
  animation: drawBox 0.6s ease-out forwards;
}

@keyframes drawBox {
  0% { box-shadow: 0 0 0 0 rgba(43, 76, 126, 0); border-color: transparent; }
  100% { box-shadow: 0 2px 10px rgba(43, 76, 126, 0.15); border-color: var(--rule-blue); }
}

/* TEACH mode step reveal animation */
.step-reveal {
  animation: inkReveal 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

@keyframes inkReveal {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Mode transition animation */
.mode-switch-wash {
  animation: pageWash 0.3s ease-out;
}

@keyframes pageWash {
  0% { opacity: 0.85; }
  100% { opacity: 1; }
}

/* Reduced Motion Override */
@media (prefers-reduced-motion: reduce) {
  .direct-answer-box, .step-reveal, .mode-switch-wash {
    animation: none !important;
    transition: none !important;
  }
}

/* Welcome Notebook Card */
.welcome-card {
  background: var(--card-bg);
  border: 1px solid rgba(43, 76, 126, 0.18);
  border-left: 5px solid var(--rule-blue);
  border-radius: 12px;
  padding: 24px 28px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-subtle);
}

.welcome-card h2 {
  font-family: 'Lora', serif;
  color: var(--rule-blue);
  font-size: 22px;
  margin-bottom: 10px;
}

.welcome-card p {
  color: var(--pencil);
  font-size: 14.5px;
  line-height: 1.7;
}

/* Custom Input Affordances (Tabs) */
.itype-affordance {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-family: 'IBM Plex Sans', sans-serif;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(43, 76, 126, 0.08);
  color: var(--rule-blue);
  border: 1px solid rgba(43, 76, 126, 0.15);
  margin-bottom: 8px;
}

.itype-voice { background: rgba(111, 176, 128, 0.12); color: var(--correct); border-color: rgba(111, 176, 128, 0.25); }
.itype-image { background: rgba(217, 119, 6, 0.1); color: #D97706; border-color: rgba(217, 119, 6, 0.25); }
.itype-file  { background: rgba(181, 72, 52, 0.1); color: var(--flag); border-color: rgba(181, 72, 52, 0.25); }

/* Buttons */
.stButton > button {
  background: var(--rule-blue) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 6px !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
  font-size: 13px !important;
  font-weight: 500 !important;
  padding: 6px 14px !important;
  transition: opacity 0.2s !important;
}

.stButton > button:hover {
  opacity: 0.9 !important;
}
</style>
""", unsafe_allow_html=True)


# ── RESPONSE RENDERER ────────────────────────────────────
# Uses Streamlit's native markdown (supports $...$ and $$...$$ math natively).
# No JavaScript needed — fully reliable.

_BADGE_WORDS = {
    "MATHEMATICS": "mode-math", "MATH": "mode-math",
    "PHYSICS": "mode-physics",
    "CHEMISTRY": "mode-chem", "CHEM": "mode-chem",
    "ORIENT": "mode-neutral", "PROBE": "mode-neutral", "UNSTICK": "mode-neutral",
    "VERIFY": "mode-neutral", "CELEBRATE": "mode-neutral",
    "TEACH": "mode-chem", "DEMONSTRATE": "mode-chem",
    "PRACTICE": "mode-chem", "ASSESS": "mode-chem", "REMEDIATE": "mode-chem",
    "CONCEPTUALIZE": "mode-physics", "FORMULATE": "mode-physics",
    "CALCULATE": "mode-physics",
}


def _extract_badges(text: str) -> tuple[str, str]:
    """
    Pull out leading [BADGE] tokens from the response and return
    (badge_html, remaining_text).
    """
    badge_html_parts = []
    pos = 0
    for m in re.finditer(r"\[([A-Z_/ ]+)\]", text):
        if m.start() > pos + 4:          # stop if badges aren't at the top
            break
        word = m.group(1).strip()
        css  = _BADGE_WORDS.get(word, "mode-neutral")
        badge_html_parts.append(
            f"<span class='mode-badge {css}'>{m.group(0)}</span>"
        )
        pos = m.end()
    remaining = text[pos:].lstrip("\n ")
    return "".join(badge_html_parts), remaining


def normalize_latex_delimiters(text: str) -> str:
    """Convert \\[ \\] and \\( \\) style LaTeX into $$ $$ and $ $ style,
    since Streamlit and KaTeX auto-render primarily listen for $ delimiters."""
    if not text:
        return ""
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)

    # Fallback for standalone [ math ] brackets (e.g. [ V = I R . ])
    def bracket_replacer(m):
        full = m.group(0)
        content = m.group(1).strip()
        # Protect badges like [TEACH], [DIRECT], [MATHEMATICS], [PHYSICS], [CHEMISTRY], [ORIENT]
        if re.match(r'^[A-Z_/ ]+$', content) and len(content) <= 20:
            return full
        math_inds = (
            '\\', '=', '+', '-', '*', '/', '^', '_', '<', '>',
            '\\frac', '\\dfrac', '\\text', '\\boxed', '\\Omega', '\\degree',
            '\\times', '\\cdot', '\\sqrt', '\\alpha', '\\beta', '\\theta',
            '\\mu', '\\rho', '\\pi', '\\Delta', '\\approx', '\\pm'
        )
        if any(ind in content for ind in math_inds) or re.search(r'[A-Za-z0-9_\{\}]+\s*=\s*[A-Za-z0-9_\{\}\\\s\.\,\+\-\*\/\(\)]+', content):
            return f"\n$$\n{content}\n$$\n"
        return full

    text = re.sub(r'\[\s*([^\]\n]+?)\s*\](?!\()', bracket_replacer, text)

    # Fallback for inline parenthesized latex like (V_2 = 120\ \text{V}) or (I = \dfrac{V}{R})
    def paren_replacer(m):
        full = m.group(0)
        content = m.group(1).strip()
        math_inds = (
            '\\text', '\\frac', '\\dfrac', '\\Omega', '\\qquad', '\\times',
            '\\cdot', '\\sqrt', '\\boxed', '\\alpha', '\\beta', '\\theta',
            '\\mu', '\\rho', '\\pi', '\\degree', '\\Delta', '_'
        )
        if any(ind in content for ind in math_inds):
            return f"${content}$"
        return full

    text = re.sub(r'\(([^()\n]+?)\)', paren_replacer, text)

    # Ensure standalone \boxed{...} outside $ or $$ is wrapped in $$
    def boxed_fixer(m):
        prefix = m.group(1)
        content = m.group(2)
        if prefix == '$':
            return m.group(0)
        return f"{prefix}$$\\boxed{{{content}}}$$"

    text = re.sub(r'(^|[^$])\\boxed\{([^{}]+)\}', boxed_fixer, text)

    # Clean up empty block math
    text = re.sub(r'\$\$\s*\$\$', '', text)
    return text


def render_response(text: str, is_latest: bool = False):
    """
    Render the AI response in a clean, notebook-style format:
    • [SUBJECT] [MODE] badges shown as chip indicators
    • Block equations ($$...$$) wrapped in a styled equation box
    • Final boxed answers in DIRECT mode receive a continuous line animation
    """
    text = normalize_latex_delimiters(text)
    badge_html, body = _extract_badges(text)

    if badge_html:
        st.markdown(badge_html, unsafe_allow_html=True)

    reveal_cls = "step-reveal" if is_latest else ""
    if reveal_cls:
        st.markdown(f"<div class='{reveal_cls}'>", unsafe_allow_html=True)

    # Split on $$ blocks so we can wrap each display equation in a styled box
    parts = re.split(r"(\$\$[\s\S]*?\$\$)", body)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("$$") and part.endswith("$$"):
            is_boxed_ans = "\\boxed" in part
            box_cls = "direct-answer-box" if is_boxed_ans else "eq-block"
            st.markdown(f"<div class='{box_cls}'>", unsafe_allow_html=True)
            st.markdown(part)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(part)

    if reveal_cls:
        st.markdown("</div>", unsafe_allow_html=True)


# ── INPUT TYPE AFFORDANCE HTML ────────────────────────────
def itype_html(it: str) -> str:
    icons = {
        "TEXT": "💬 Text Question",
        "VOICE_TRANSCRIPT": "🎙️ Spoken Audio",
        "IMAGE_HANDWRITTEN": "📷 Handwritten Sheet",
        "IMAGE_TEXTBOOK": "📷 Textbook Snapshot",
        "FILE_PDF": "📄 Document Worksheet",
    }
    css = {
        "TEXT": "",
        "VOICE_TRANSCRIPT": "itype-voice",
        "IMAGE_HANDWRITTEN": "itype-image",
        "IMAGE_TEXTBOOK": "itype-image",
        "FILE_PDF": "itype-file",
    }
    cls = css.get(it, "")
    label = icons.get(it, it)
    return f"<div class='itype-affordance {cls}'>{label}</div>"


def subject_badge_html(subject: str) -> str:
    info = SUBJECTS.get(subject, SUBJECTS["MATHEMATICS"])
    css_map = {"MATHEMATICS": "subj-math", "SCIENCE": "subj-science"}
    css = css_map.get(subject, "subj-math")
    return f"<span class='{css}'>{info['avatar']} {subject}</span>"


# ── NEW-PROBLEM DETECTION ────────────────────────────────
_CONTINUATION_KEYWORDS = {
    "hint", "next", "stuck", "continue", "step", "explain",
    "more", "go on", "why", "how", "what about", "show me",
}


def _is_new_problem(new_msg: str, messages: list[dict], input_type: str) -> bool:
    """
    Heuristic: detect when the student starts a new problem so we can
    treat it as a fresh problem context automatically.
    """
    if input_type not in ("TEXT", "VOICE_TRANSCRIPT"):
        return False

    msg_lower = new_msg.lower().strip()

    # Short continuations are not new problems
    if len(msg_lower.split()) <= 3:
        for kw in _CONTINUATION_KEYWORDS:
            if kw in msg_lower:
                return False

    # Find the last user message
    last_user_msg = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last_user_msg = m["content"].lower().strip()
            break

    if not last_user_msg:
        return True  # First message is always a new problem

    # Word-overlap similarity check
    new_words = set(msg_lower.split())
    old_words = set(last_user_msg.split())
    if not new_words or not old_words:
        return True

    overlap = len(new_words & old_words)
    similarity = overlap / max(len(new_words), len(old_words))

    # If less than 40% word overlap, treat as a new problem
    return similarity < 0.4


# ── PDF QUESTION EXTRACTION ──────────────────────────────
_QUESTION_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:Q\.?\s*)?(\d{1,3})\s*[\.\)\:]",
)


def _extract_questions_from_text(text: str) -> list[str]:
    """
    Split extracted PDF text into individual questions by numbering patterns.
    """
    matches = list(_QUESTION_PATTERN.finditer(text))
    if not matches:
        return [text.strip()] if text.strip() else []

    questions = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        q_text = text[start:end].strip()
        if q_text:
            questions.append(q_text)

    return questions


# ── SESSION STATE ─────────────────────────────────────────
def init_session():
    defaults = {
        "messages":        [],
        "mode":            "TEACH",
        "current_chapter": "General",
        "active_subject":  "MATHEMATICS",
        "mathmate":        None,
        "problem_count":   0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state.mathmate is None:
        with st.spinner("⚙️ Loading MathMate v4.0 engine..."):
            st.session_state.mathmate = MathMate()

init_session()
mm: MathMate = st.session_state.mathmate

CHAPTERS = [
    "General",
    "Chapter 1", "Chapter 2", "Chapter 3", "Chapter 4", "Chapter 5",
    "Chapter 6", "Chapter 7", "Chapter 8", "Chapter 9", "Chapter 10",
    "Chapter 11", "Chapter 12", "Chapter 13", "Chapter 14", "Chapter 15",
    "Unit 1", "Unit 2", "Unit 3", "Unit 4", "Unit 5",
    "Unit 6", "Unit 7", "Unit 8", "Unit 9", "Unit 10",
]


# ── SIDEBAR (STUDY DESK) ──────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px 0;'>
      <div style='font-size:38px;'>🎓</div>
      <div style='font-family:"Lora",serif;font-size:20px;color:var(--rule-blue);font-weight:600;'>MathMate Desk</div>
      <div style='font-size:11px;color:var(--pencil);font-family:"IBM Plex Sans",sans-serif;margin-top:2px;'>NCERT Class 10 Paper & Pencil Tutor</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # ── MODE SELECTOR ────────────────────────────────────
    st.markdown("<div class='desk-section-header'>🎯 Tutor Mode</div>", unsafe_allow_html=True)

    mode_choice = st.radio(
        "Mode",
        ["🧑‍🏫 Teach me (step by step)", "⚡ Just solve it (full answer)"],
        horizontal=True,
        key="mode_select",
        label_visibility="collapsed",
    )
    st.session_state.mode = "TEACH" if "Teach" in mode_choice else "DIRECT"

    # Show current mode indicator
    if st.session_state.mode == "TEACH":
        st.markdown("<div class='desk-mode-box teach'>🧑‍🏫 TEACH — Socratic notebook guidance</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='desk-mode-box direct'>⚡ DIRECT — Full worked solution</div>", unsafe_allow_html=True)

    st.divider()

    # ── SUBJECT SWITCHER ──────────────────────────────────
    st.markdown("<div class='desk-section-header'>📚 Active Subject</div>", unsafe_allow_html=True)

    subj_options = list(SUBJECTS.keys())
    subj_labels  = [SUBJECTS[s]["label"] for s in subj_options]
    current_idx  = subj_options.index(st.session_state.active_subject)

    selected_label = st.radio(
        "subject",
        subj_labels,
        index=current_idx,
        label_visibility="collapsed",
    )
    new_subject = subj_options[subj_labels.index(selected_label)]

    if new_subject != st.session_state.active_subject:
        st.session_state.active_subject  = new_subject
        st.session_state.messages        = []
        st.session_state.current_chapter = "General"
        st.rerun()

    active_subj = st.session_state.active_subject
    st.divider()

    # ── PER-SUBJECT KNOWLEDGE BASES ───────────────────────
    st.markdown("<div class='desk-section-header'>📖 Desk Textbooks</div>", unsafe_allow_html=True)

    for subj_key, subj_info in SUBJECTS.items():
        built = is_index_built(subj_key)
        status_css   = "idx-ready" if built else "idx-missing"
        status_icon  = "✅" if built else "○"
        status_label = "Knowledge base ready" if built else "No PDF loaded"

        st.markdown(
            f"<div class='desk-kb-card {status_css}'>"
            f"<div>{status_icon} <strong>{subj_info['label']}</strong></div>"
            f"<div style='font-size:11px;color:var(--pencil);margin-top:2px;'>{status_label}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── UPLOAD FOR ACTIVE SUBJECT ─────────────────────────
    active_info = SUBJECTS[active_subj]
    st.markdown(
        f"<div class='desk-section-header'>{active_info['avatar']} Upload {active_info['label']} PDF</div>",
        unsafe_allow_html=True,
    )

    uploaded_pdf = st.file_uploader(
        f"{active_info['label']} PDF",
        type=["pdf"],
        key=f"pdf_upload_{active_subj}",
        label_visibility="collapsed",
    )

    if uploaded_pdf and st.button("⚙️ Build Knowledge Base", use_container_width=True):
        prog = st.progress(0.0)
        stat = st.empty()

        def on_prog(step, pct):
            prog.progress(pct)
            stat.markdown(f"<span style='font-size:12px;color:var(--pencil);'>{step}</span>", unsafe_allow_html=True)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(uploaded_pdf.read())
            tmp_path = tmp.name
        try:
            build_faiss_from_pdf(tmp_path, progress_callback=on_prog, subject=active_subj)
            mm.reload_index(active_subj)
            stat.empty()
            st.success(f"🎉 {active_info['label']} knowledge base ready!")
            st.rerun()
        except Exception as e:
            st.error(f"Build failed: {e}")
        finally:
            os.unlink(tmp_path)

    st.divider()

    # ── CHAPTER / TOPIC ───────────────────────────────────
    st.markdown("<div class='desk-section-header'>🔖 Chapter / Unit</div>", unsafe_allow_html=True)
    sel_ch = st.selectbox(
        "chapter",
        CHAPTERS,
        index=CHAPTERS.index(st.session_state.current_chapter) if st.session_state.current_chapter in CHAPTERS else 0,
        label_visibility="collapsed",
    )
    if sel_ch != st.session_state.current_chapter:
        st.session_state.current_chapter = sel_ch

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 New Problem", use_container_width=True):
            st.session_state.problem_count += 1
            st.rerun()
    with c2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.divider()
    st.markdown("<div style='font-size:11px;color:var(--pencil);text-align:center;'>CBSE NCERT Class 10 Tutor<br/>Paper & Chalkboard Edition</div>", unsafe_allow_html=True)


# ── MAIN AREA ─────────────────────────────────────────────
active_info = SUBJECTS[active_subj]

st.markdown(f"""
<div style='margin-bottom:10px;display:flex;align-items:center;gap:14px;'>
  <div style='font-size:32px;'>{active_info['avatar']}</div>
  <div>
    <div style='font-size:26px;font-weight:600;color:#e2e8f0;'>MathMate <span style="color:{active_info['color']};">v4.0</span></div>
    <div style='font-size:13px;color:#64748b;margin-top:2px;'>{active_info['description']} · NCERT Class 10</div>
  </div>
  <div style='margin-left:auto;'>{subject_badge_html(active_subj)}</div>
</div>""", unsafe_allow_html=True)

if st.session_state.current_chapter != "General":
    st.markdown(f"<div class='chapter-badge'>{st.session_state.current_chapter}</div>", unsafe_allow_html=True)

# Welcome card
index_loaded = mm.index_loaded  # dict {subject: bool}
active_index_ready = index_loaded.get(active_subj, False)

if not st.session_state.messages:
    st.markdown(f"""
    <div class='welcome-card'>
      <h2>{active_info['avatar']} Welcome to MathMate v4.0!</h2>
      <p>
        Your <strong style='color:{active_info['color']};'>NCERT Class 10 AI Tutor</strong> with two modes:<br/><br/>
        🧑‍🏫 <strong>Teach mode</strong> — I guide you step by step (Socratic method), never giving the answer directly<br/>
        ⚡ <strong>Direct mode</strong> — I give you the complete worked solution immediately<br/><br/>
        💬 <strong>Text</strong> — type a question or problem directly<br/>
        🎙️ <strong>Voice</strong> — speak your question, Whisper transcribes it<br/>
        📷 <strong>Image</strong> — photo of your handwriting or a textbook page<br/>
        📄 <strong>Document</strong> — upload a worksheet or question paper PDF<br/><br/>
        {'✅ <strong>' + active_info["label"] + '</strong> knowledge base is ready — start asking!' if active_index_ready else '⚠️ Upload the <strong>' + active_info["label"] + '</strong> PDF in the sidebar first to enable context-aware answers.'}
      </p>
    </div>""", unsafe_allow_html=True)

# ── RENDER CHAT HISTORY ───────────────────────────────────
for msg in st.session_state.messages:
    avatar = "🧑‍🎓" if msg["role"] == "user" else active_info["avatar"]
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "user":
            itype = msg.get("input_type", "TEXT")
            st.markdown(itype_html(itype), unsafe_allow_html=True)
            st.markdown(msg["content"])
        else:
            render_response(msg["content"])


# ── DISPATCH HELPER ───────────────────────────────────────
def _dispatch(user_msg: str, input_type: str, engine: MathMate, file_text: str = ""):
    """Add user message, call MathMate, update state."""
    subject = st.session_state.active_subject
    subj_info = SUBJECTS[subject]
    mode = st.session_state.mode

    # New-problem detection
    if _is_new_problem(user_msg, st.session_state.messages, input_type):
        st.session_state.problem_count += 1

    st.session_state.messages.append({"role": "user", "content": user_msg, "input_type": input_type})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(itype_html(input_type), unsafe_allow_html=True)
        st.markdown(user_msg)

    with st.chat_message("assistant", avatar=subj_info["avatar"]):
        with st.spinner(f"{subj_info['avatar']} Thinking..."):
            response = engine.chat(
                user_message=user_msg,
                chat_history=st.session_state.messages[:-1],
                mode=mode,
                current_chapter=st.session_state.current_chapter,
                input_type=input_type,
                file_text=file_text,
                subject=subject,
            )
        render_response(response, is_latest=True)

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.rerun()


# ── INPUT AREA ────────────────────────────────────────────
if not active_index_ready:
    st.info(f"📤 Upload the **{active_info['label']} PDF** in the sidebar, then click **Build Knowledge Base**.")
    st.chat_input(f"Upload {active_info['label']} PDF first...", disabled=True)
else:
    tab_text, tab_voice, tab_image, tab_file = st.tabs(["💬 Text", "🎙️ Voice", "📷 Image", "📄 Document"])

    # ── TEXT TAB ─────────────────────────────────────────
    with tab_text:
        if prompt := st.chat_input(
            f"Ask a {active_info['label']} question from your NCERT textbook...",
            key="chat_text",
        ):
            _dispatch(prompt, "TEXT", mm)

    # ── VOICE TAB ────────────────────────────────────────
    with tab_voice:
        st.markdown("<div style='font-size:12px;color:#94a3b8;margin-bottom:10px;'>Record your question. MathMate will transcribe and respond.</div>", unsafe_allow_html=True)
        audio = st.audio_input("Hold to record", key="audio_input")
        if audio and st.button("🎙️ Send Voice Question", use_container_width=True, key="send_voice"):
            with st.spinner("Transcribing with Whisper..."):
                transcript, ok = voice_to_text(audio.read(), filename=audio.name if hasattr(audio, "name") else "audio.wav")
            if not ok:
                st.error(transcript)
            else:
                st.info(f"📝 Transcript: *{transcript}*")
                _dispatch(transcript, "VOICE_TRANSCRIPT", mm)

    # ── IMAGE TAB ────────────────────────────────────────
    with tab_image:
        st.markdown("<div style='font-size:12px;color:#94a3b8;margin-bottom:10px;'>Upload a photo of your handwritten working or a textbook page (JPG / PNG / WEBP).</div>", unsafe_allow_html=True)
        img_file = st.file_uploader("Upload image", type=["jpg","jpeg","png","webp"], key="img_upload", label_visibility="collapsed")
        if img_file and st.button("📷 Analyse Image", use_container_width=True, key="send_image"):
            with st.spinner("Analysing image with Vision LLM..."):
                mime = mime_from_filename(img_file.name)
                desc, ok = image_to_description(img_file.read(), mime_type=mime)
            if not ok:
                st.error(desc)
            else:
                itype = detect_image_type(desc)
                _dispatch(desc, itype, mm)

    # ── FILE TAB ─────────────────────────────────────────
    with tab_file:
        st.markdown("<div style='font-size:12px;color:#94a3b8;margin-bottom:10px;'>Upload a worksheet or question paper PDF. MathMate will list all questions found.</div>", unsafe_allow_html=True)
        ws_file = st.file_uploader("Upload worksheet PDF", type=["pdf"], key="ws_upload", label_visibility="collapsed")
        if ws_file and st.button("📄 Load Document", use_container_width=True, key="send_file"):
            with st.spinner("Extracting document text..."):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(ws_file.read())
                    tmp_path = tmp.name
                try:
                    doc = fitz.open(tmp_path)
                    file_text = "\n\n".join(p.get_text("text") for p in doc)
                    doc.close()
                finally:
                    os.unlink(tmp_path)

            # Extract individual questions instead of silently truncating
            questions = _extract_questions_from_text(file_text)

            if questions:
                q_summary = "\n".join(
                    f"  {i+1}. {q[:120]}{'…' if len(q) > 120 else ''}"
                    for i, q in enumerate(questions)
                )
                msg = f"[Document uploaded: {ws_file.name}]\n\n**{len(questions)} questions found:**\n{q_summary}"
            else:
                msg = f"[Document uploaded: {ws_file.name}]\n\n{file_text[:500]}{'…' if len(file_text) > 500 else ''}"

            # If genuinely too long for context, condense and warn
            condensed = False
            if len(file_text) > 12000:
                condensed = True
                file_text_for_model = file_text[:12000] + "\n\n[... remaining text condensed for context limit]"
            else:
                file_text_for_model = file_text

            if condensed:
                st.warning("⚠️ The document was very long. Some content at the end was condensed to fit the model's context window. All detected questions are listed above.")

            _dispatch(msg, "FILE_PDF", mm, file_text=file_text_for_model)
