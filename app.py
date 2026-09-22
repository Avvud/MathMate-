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
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
#MainMenu, footer { visibility: hidden; }
.stApp { background: #080a0f; color: #e2e8f0; }
[data-testid="stSidebar"] { background: #0c0e16 !important; border-right: 1px solid rgba(255,255,255,0.07); }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stChatMessage"] { background: #11141c; border: 1px solid rgba(255,255,255,0.07); border-radius: 14px; margin-bottom: 14px; }
[data-testid="stChatInput"] { background: #11141c !important; border: 1px solid rgba(110,231,183,0.3) !important; border-radius: 12px !important; }
[data-testid="stChatInput"]:focus-within { border-color: rgba(110,231,183,0.7) !important; box-shadow: 0 0 0 2px rgba(110,231,183,0.15) !important; }
.stButton > button { background: rgba(110,231,183,0.08) !important; border: 1px solid rgba(110,231,183,0.25) !important; color: #6ee7b7 !important; border-radius: 8px !important; font-family: 'DM Mono', monospace !important; font-size: 12px !important; transition: all 0.2s !important; }
.stButton > button:hover { background: rgba(110,231,183,0.18) !important; transform: translateY(-1px) !important; }
[data-testid="stFileUploader"] { background: #11141c !important; border: 1px dashed rgba(129,140,248,0.35) !important; border-radius: 10px !important; }
hr { border-color: rgba(255,255,255,0.07) !important; }
/* Welcome card */
.welcome-card { background:linear-gradient(135deg,rgba(110,231,183,0.06),rgba(129,140,248,0.06)); border:1px solid rgba(110,231,183,0.15); border-radius:18px; padding:28px 32px; margin-bottom:24px; }
.welcome-card h2 { color:#6ee7b7; margin-bottom:8px; font-size:22px; }
.welcome-card p { color:#94a3b8; font-size:14px; line-height:1.7; margin:0; }
/* Input type badges */
.itype-badge { font-family:'DM Mono',monospace; font-size:10px; letter-spacing:.08em; padding:2px 8px; border-radius:4px; display:inline-block; margin-bottom:6px; }
.it-text  { background:rgba(96,165,250,0.1);  color:#60a5fa; border:1px solid rgba(96,165,250,0.2); }
.it-voice { background:rgba(167,139,250,0.1); color:#a78bfa; border:1px solid rgba(167,139,250,0.2); }
.it-image { background:rgba(251,191,36,0.1);  color:#fbbf24; border:1px solid rgba(251,191,36,0.2); }
.it-file  { background:rgba(244,114,182,0.1); color:#f472b6; border:1px solid rgba(244,114,182,0.2); }
/* Chapter badge */
.chapter-badge { font-family:'DM Mono',monospace; font-size:11px; background:rgba(129,140,248,0.1); color:#818cf8; border:1px solid rgba(129,140,248,0.2); border-radius:6px; padding:4px 10px; display:inline-block; margin-bottom:12px; }
/* Subject badges */
.subj-math    { background:rgba(110,231,183,0.12); color:#6ee7b7; border:1px solid rgba(110,231,183,0.3); border-radius:6px; padding:3px 10px; font-family:'DM Mono',monospace; font-size:11px; display:inline-block; }
.subj-science { background:rgba(96,165,250,0.12); color:#60a5fa; border:1px solid rgba(96,165,250,0.3); border-radius:6px; padding:3px 10px; font-family:'DM Mono',monospace; font-size:11px; display:inline-block; }
/* Index status per subject */
.idx-ready { background:rgba(110,231,183,0.08); border:1px solid rgba(110,231,183,0.2); border-radius:8px; padding:6px 10px; font-size:12px; color:#6ee7b7; font-family:'DM Mono',monospace; }
.idx-missing { background:rgba(255,255,255,0.03); border:1px dashed rgba(255,255,255,0.1); border-radius:8px; padding:6px 10px; font-size:12px; color:#475569; font-family:'DM Mono',monospace; }
/* ── Response / chat area readable styles ── */
[data-testid="stChatMessage"] p { font-size:15px !important; line-height:1.85 !important; color:#dde4f0 !important; }
[data-testid="stChatMessage"] li { font-size:15px !important; line-height:1.8 !important; margin-bottom:4px; }
[data-testid="stChatMessage"] strong { color:#e2e8f0 !important; }
[data-testid="stChatMessage"] code { font-family:'DM Mono',monospace !important; font-size:13px !important; background:rgba(129,140,248,0.13) !important; color:#c4b5fd !important; padding:2px 7px !important; border-radius:4px !important; }
/* Mode badge: [ORIENT], [TEACH], etc. parsed by render_response */
.mode-badge { display:inline-block; font-family:'DM Mono',monospace; font-size:11px; letter-spacing:.07em; padding:3px 10px; border-radius:5px; margin-bottom:10px; margin-right:6px; font-weight:500; }
.mode-math    { background:rgba(110,231,183,0.12); color:#6ee7b7; border:1px solid rgba(110,231,183,0.3); }
.mode-physics { background:rgba(96,165,250,0.12);  color:#60a5fa; border:1px solid rgba(96,165,250,0.3); }
.mode-chem    { background:rgba(251,146,60,0.12);  color:#fb923c; border:1px solid rgba(251,146,60,0.3); }
.mode-neutral { background:rgba(129,140,248,0.12); color:#a5b4fc; border:1px solid rgba(129,140,248,0.3); }
/* Equation block wrapper (wraps $$...$$) */
.eq-block { background:rgba(110,231,183,0.05); border-left:3px solid rgba(110,231,183,0.4); border-radius:0 8px 8px 0; padding:12px 18px; margin:12px 0; overflow-x:auto; }
/* Step separator */
.step-block { border-left:2px solid rgba(129,140,248,0.3); padding-left:14px; margin:10px 0; }
/* Mode selector styling */
.mode-indicator { font-family:'DM Mono',monospace; font-size:11px; letter-spacing:.08em; padding:4px 12px; border-radius:6px; display:inline-block; margin-top:6px; }
.mode-teach  { background:rgba(110,231,183,0.12); color:#6ee7b7; border:1px solid rgba(110,231,183,0.3); }
.mode-direct { background:rgba(251,191,36,0.12);  color:#fbbf24; border:1px solid rgba(251,191,36,0.3); }
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


def render_response(text: str):
    """
    Render the AI response in a clean, readable format:
    • [SUBJECT] [MODE] badges shown as coloured chips
    • Block equations ($$...$$) wrapped in a highlighted box
    • Everything else rendered via st.markdown (handles $...$ inline math,
      bold, bullet lists, headers, etc.)
    """
    badge_html, body = _extract_badges(text)

    if badge_html:
        st.markdown(badge_html, unsafe_allow_html=True)

    # Split on $$ blocks so we can wrap each display equation in a styled box
    parts = re.split(r"(\$\$[\s\S]*?\$\$)", body)

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("$$") and part.endswith("$$"):
            st.markdown("<div class='eq-block'>", unsafe_allow_html=True)
            st.markdown(part)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.markdown(part)


# ── INPUT TYPE BADGE HTML ─────────────────────────────────
def itype_html(it: str) -> str:
    icons = {"TEXT":"💬 TEXT","VOICE_TRANSCRIPT":"🎙️ VOICE","IMAGE_HANDWRITTEN":"📷 HANDWRITTEN","IMAGE_TEXTBOOK":"📷 TEXTBOOK","FILE_PDF":"📄 FILE"}
    css   = {"TEXT":"it-text","VOICE_TRANSCRIPT":"it-voice","IMAGE_HANDWRITTEN":"it-image","IMAGE_TEXTBOOK":"it-image","FILE_PDF":"it-file"}
    cls  = css.get(it, "it-text")
    label = icons.get(it, it)
    return f"<div class='itype-badge {cls}'>{label}</div>"


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


# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px 0;'>
      <div style='font-size:38px;'>🎓</div>
      <div style='font-family:"DM Mono",monospace;font-size:19px;color:#6ee7b7;font-weight:500;letter-spacing:.05em;'>MathMate</div>
      <div style='font-size:10px;color:#334155;font-family:"DM Mono",monospace;margin-top:4px;'>v4.0 · NCERT Class 10 · AI Tutor</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # ── MODE SELECTOR ────────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#fbbf24;margin-bottom:10px;'>🎯 Tutor Mode</div>", unsafe_allow_html=True)

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
        st.markdown("<div class='mode-indicator mode-teach'>🧑‍🏫 TEACH — Socratic guidance</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='mode-indicator mode-direct'>⚡ DIRECT — Full solutions</div>", unsafe_allow_html=True)

    st.divider()

    # ── SUBJECT SWITCHER ──────────────────────────────────
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#818cf8;margin-bottom:10px;'>🎯 Active Subject</div>", unsafe_allow_html=True)

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
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#6ee7b7;margin-bottom:10px;'>📚 Knowledge Bases</div>", unsafe_allow_html=True)

    for subj_key, subj_info in SUBJECTS.items():
        built = is_index_built(subj_key)
        status_css   = "idx-ready" if built else "idx-missing"
        status_icon  = "✅" if built else "○"
        status_label = "Index ready" if built else "No PDF yet"

        st.markdown(
            f"<div class='{status_css}' style='margin-bottom:6px;'>"
            f"{status_icon} <strong>{subj_info['label']}</strong> — {status_label}"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    # ── UPLOAD FOR ACTIVE SUBJECT ─────────────────────────
    active_info = SUBJECTS[active_subj]
    st.markdown(
        f"<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:{active_info['color']};margin-bottom:8px;'>"
        f"{active_info['avatar']} Upload {active_info['label']} PDF</div>",
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
            stat.markdown(f"<span style='font-size:12px;color:#94a3b8;'>{step}</span>", unsafe_allow_html=True)

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
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#818cf8;margin-bottom:10px;'>📖 Chapter / Topic</div>", unsafe_allow_html=True)
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
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:10px;color:#1e293b;text-align:center;'>Groq · LLM · Whisper · Vision<br/>Teach & Direct Modes · CBSE NCERT Class 10</div>", unsafe_allow_html=True)


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
        render_response(response)

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
