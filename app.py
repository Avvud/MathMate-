"""
app.py — MathMate v2.1 Multimodal Streamlit UI
NCERT Class 10 Socratic Math Tutor
"""

import os, json, tempfile
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

load_dotenv()

from build_index import build_faiss_from_pdf, is_index_built
from mathmate import MathMate
from guard import is_explicit_insist
from multimodal import voice_to_text, image_to_description, detect_image_type, mime_from_filename
import fitz  # PyMuPDF — for worksheet PDF extraction

st.set_page_config(
    page_title="MathMate — NCERT Class 10 Tutor",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
#MainMenu, footer { visibility: hidden; }
.stApp { background: #0a0c11; color: #e2e8f0; }
[data-testid="stSidebar"] { background: #0f1118 !important; border-right: 1px solid rgba(255,255,255,0.07); }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stChatMessage"] { background: #13161d; border: 1px solid rgba(255,255,255,0.07); border-radius: 12px; margin-bottom: 12px; }
[data-testid="stChatInput"] { background: #13161d !important; border: 1px solid rgba(110,231,183,0.3) !important; border-radius: 12px !important; }
[data-testid="stChatInput"]:focus-within { border-color: rgba(110,231,183,0.7) !important; box-shadow: 0 0 0 2px rgba(110,231,183,0.15) !important; }
.stButton > button { background: rgba(110,231,183,0.08) !important; border: 1px solid rgba(110,231,183,0.25) !important; color: #6ee7b7 !important; border-radius: 8px !important; font-family: 'DM Mono', monospace !important; font-size: 12px !important; transition: all 0.2s !important; }
.stButton > button:hover { background: rgba(110,231,183,0.18) !important; transform: translateY(-1px) !important; }
[data-testid="stFileUploader"] { background: #13161d !important; border: 1px dashed rgba(129,140,248,0.35) !important; border-radius: 10px !important; }
hr { border-color: rgba(255,255,255,0.07) !important; }
.hint-badge { display:inline-block; font-family:'DM Mono',monospace; font-size:11px; padding:3px 10px; border-radius:20px; margin-right:4px; }
.h-active { background:rgba(110,231,183,0.15); color:#6ee7b7; border:1px solid rgba(110,231,183,0.3); }
.h-inactive { background:rgba(255,255,255,0.04); color:#334155; border:1px solid rgba(255,255,255,0.07); }
.welcome-card { background:linear-gradient(135deg,rgba(110,231,183,0.07),rgba(129,140,248,0.07)); border:1px solid rgba(110,231,183,0.18); border-radius:16px; padding:28px 32px; margin-bottom:24px; }
.welcome-card h2 { color:#6ee7b7; margin-bottom:8px; font-size:22px; }
.welcome-card p { color:#94a3b8; font-size:14px; line-height:1.6; margin:0; }
.itype-badge { font-family:'DM Mono',monospace; font-size:10px; letter-spacing:.08em; padding:2px 8px; border-radius:4px; display:inline-block; margin-bottom:6px; }
.it-text  { background:rgba(96,165,250,0.1);  color:#60a5fa; border:1px solid rgba(96,165,250,0.2); }
.it-voice { background:rgba(167,139,250,0.1); color:#a78bfa; border:1px solid rgba(167,139,250,0.2); }
.it-image { background:rgba(251,191,36,0.1);  color:#fbbf24; border:1px solid rgba(251,191,36,0.2); }
.it-file  { background:rgba(244,114,182,0.1); color:#f472b6; border:1px solid rgba(244,114,182,0.2); }
.chapter-badge { font-family:'DM Mono',monospace; font-size:11px; background:rgba(129,140,248,0.1); color:#818cf8; border:1px solid rgba(129,140,248,0.2); border-radius:6px; padding:4px 10px; display:inline-block; margin-bottom:12px; }
.insist-badge { font-family:'DM Mono',monospace; font-size:10px; padding:3px 10px; border-radius:20px; }
.ig-open   { background:rgba(248,113,113,0.15); color:#f87171; border:1px solid rgba(248,113,113,0.3); }
.ig-closed { background:rgba(255,255,255,0.04); color:#334155; border:1px solid rgba(255,255,255,0.07); }
</style>
""", unsafe_allow_html=True)


# ── KATEX RENDER ─────────────────────────────────────────
def render_katex(text: str):
    """Render assistant response with full KaTeX math support inside an iframe."""
    text_json = json.dumps(text)
    height = max(120, min(900, len(text) * 0.6 + 80))
    components.html(f"""<!DOCTYPE html><html><head>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js" onload="init()"></script>
<style>
*{{box-sizing:border-box;}}
body{{background:transparent;color:#dde4f0;font-family:'DM Sans',sans-serif;font-size:14px;line-height:1.8;margin:0;padding:2px 4px;word-wrap:break-word;}}
p{{margin:0 0 10px 0;}}
.katex{{color:#86efac;}}
.katex-display{{overflow-x:auto;padding:6px 0;}}
</style></head><body><div id="c"></div>
<script>
const raw={text_json};
function init(){{
  const el=document.getElementById('c');
  el.innerHTML=raw.split('\\n\\n').map(p=>
    '<p>'+p.split('\\n').join('<br>')+'</p>'
  ).join('');
  renderMathInElement(document.body,{{
    delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'$',right:'$',display:false}}],
    throwOnError:false
  }});
}}
</script></body></html>""", height=int(height), scrolling=False)


# ── INPUT TYPE BADGE HTML ─────────────────────────────────
def itype_html(it: str) -> str:
    icons = {"TEXT":"💬 TEXT","VOICE_TRANSCRIPT":"🎙️ VOICE","IMAGE_HANDWRITTEN":"📷 HANDWRITTEN","IMAGE_TEXTBOOK":"📷 TEXTBOOK","FILE_PDF":"📄 FILE"}
    css   = {"TEXT":"it-text","VOICE_TRANSCRIPT":"it-voice","IMAGE_HANDWRITTEN":"it-image","IMAGE_TEXTBOOK":"it-image","FILE_PDF":"it-file"}
    cls  = css.get(it, "it-text")
    label = icons.get(it, it)
    return f"<div class='itype-badge {cls}'>{label}</div>"


# ── SESSION STATE ─────────────────────────────────────────
def init_session():
    defaults = {
        "messages": [],
        "hint_count": 0,
        "insist_count": 0,
        "current_chapter": "General",
        "mathmate": None,
        "index_ready": is_index_built(),
        "problem_count": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    if st.session_state.mathmate is None:
        with st.spinner("Loading MathMate engine..."):
            st.session_state.mathmate = MathMate()

init_session()
mm: MathMate = st.session_state.mathmate

CHAPTERS = [
    "General","Ch 1 — Real Numbers","Ch 2 — Polynomials",
    "Ch 3 — Pair of Linear Equations","Ch 4 — Quadratic Equations",
    "Ch 5 — Arithmetic Progressions","Ch 6 — Triangles",
    "Ch 7 — Coordinate Geometry","Ch 8 — Introduction to Trigonometry",
    "Ch 9 — Applications of Trigonometry","Ch 10 — Circles",
    "Ch 11 — Constructions","Ch 12 — Areas Related to Circles",
    "Ch 13 — Surface Areas and Volumes","Ch 14 — Statistics",
]


# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:16px 0 8px 0;'>
      <div style='font-size:36px;'>📐</div>
      <div style='font-family:"DM Mono",monospace;font-size:18px;color:#6ee7b7;font-weight:500;letter-spacing:.05em;'>MathMate</div>
      <div style='font-size:10px;color:#334155;font-family:"DM Mono",monospace;margin-top:4px;'>v2.1 Multimodal · NCERT Class 10</div>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # Knowledge base
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#6ee7b7;margin-bottom:10px;'>📚 Knowledge Base</div>", unsafe_allow_html=True)
    if st.session_state.index_ready:
        st.success("✅ NCERT index loaded")
    else:
        st.warning("⚠️ Upload NCERT PDF to begin")

    uploaded_ncert = st.file_uploader("NCERT Class 10 Maths PDF", type=["pdf"], key="pdf_upload", label_visibility="collapsed")
    if uploaded_ncert and st.button("⚙️ Build Knowledge Base", use_container_width=True):
        prog = st.progress(0.0); stat = st.empty()
        def on_prog(step, pct): prog.progress(pct); stat.markdown(f"<span style='font-size:12px;color:#94a3b8;'>{step}</span>", unsafe_allow_html=True)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(uploaded_ncert.read()); tmp_path = tmp.name
        try:
            build_faiss_from_pdf(tmp_path, progress_callback=on_prog)
            mm.reload_index(); st.session_state.index_ready = True
            stat.empty(); st.success("🎉 Knowledge base ready!"); st.rerun()
        except Exception as e:
            st.error(f"Build failed: {e}")
        finally:
            os.unlink(tmp_path)

    st.divider()

    # Chapter selector
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#818cf8;margin-bottom:10px;'>📖 Chapter</div>", unsafe_allow_html=True)
    sel_ch = st.selectbox("chapter", CHAPTERS, index=CHAPTERS.index(st.session_state.current_chapter) if st.session_state.current_chapter in CHAPTERS else 0, label_visibility="collapsed")
    if sel_ch != st.session_state.current_chapter:
        st.session_state.current_chapter = sel_ch

    st.divider()

    # Hint progress
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:11px;letter-spacing:.1em;text-transform:uppercase;color:#fbbf24;margin-bottom:10px;'>💡 Hint Progress</div>", unsafe_allow_html=True)
    h, max_h = st.session_state.hint_count, 4
    dots = "".join(f"<span class='hint-badge {'h-active' if i < h else 'h-inactive'}'>●</span>" for i in range(max_h))
    st.markdown(dots, unsafe_allow_html=True)
    if h == 0: hl, hc = "No hints used yet", "#64748b"
    elif h < max_h: hl, hc = f"{h}/{max_h} hints given", "#fbbf24"
    else: hl, hc = "Next step will be shown 🔓", "#f87171"
    st.markdown(f"<div style='font-size:11px;color:{hc};font-family:\"DM Mono\",monospace;margin-top:6px;'>{hl}</div>", unsafe_allow_html=True)

    # Insist gate status
    ic = st.session_state.insist_count
    gate_near = st.session_state.hint_count >= 2 and ic >= 1
    ig_label = "🔓 Answer gate OPEN" if gate_near else f"🔒 Insist demands: {ic}/1"
    ig_css   = "ig-open" if gate_near else "ig-closed"
    st.markdown(f"<div class='insist-badge {ig_css}' style='margin-top:10px;display:inline-block;'>{ig_label}</div>", unsafe_allow_html=True)

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 New Problem", use_container_width=True):
            st.session_state.hint_count = 0; st.session_state.insist_count = 0
            st.session_state.problem_count += 1; st.rerun()
    with c2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []; st.session_state.hint_count = 0
            st.session_state.insist_count = 0; st.rerun()

    st.divider()
    st.markdown("<div style='font-family:\"DM Mono\",monospace;font-size:10px;color:#1e293b;text-align:center;'>Groq · llama-3.3-70b · Whisper · Vision<br/>Socratic Method · CBSE NCERT</div>", unsafe_allow_html=True)


# ── MAIN AREA ─────────────────────────────────────────────
st.markdown("""
<div style='margin-bottom:8px;'>
  <div style='font-size:28px;font-weight:600;color:#e2e8f0;'>📐 MathMate</div>
  <div style='font-size:13px;color:#64748b;margin-top:2px;'>Multimodal NCERT Class 10 Socratic Tutor · v2.1</div>
</div>""", unsafe_allow_html=True)

if st.session_state.current_chapter != "General":
    st.markdown(f"<div class='chapter-badge'>{st.session_state.current_chapter}</div>", unsafe_allow_html=True)

# Welcome card
if not st.session_state.messages:
    st.markdown("""
    <div class='welcome-card'>
      <h2>👋 Welcome to MathMate!</h2>
      <p>
        Your <strong style='color:#6ee7b7;'>Socratic NCERT Class 10 Maths tutor</strong> — I guide you to the answer, never just give it.<br/><br/>
        💬 <strong>Text</strong> — type a problem directly<br/>
        🎙️ <strong>Voice</strong> — speak your question, Whisper transcribes it<br/>
        📷 <strong>Image</strong> — photo of your handwriting or a textbook page<br/>
        📄 <strong>File</strong> — upload a worksheet PDF and pick a question<br/><br/>
        Upload the <strong>NCERT PDF</strong> in the sidebar first to enable context-aware hints.
      </p>
    </div>""", unsafe_allow_html=True)

    st.markdown("<div style='font-size:12px;color:#475569;font-family:\"DM Mono\",monospace;text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px;'>Try asking...</div>", unsafe_allow_html=True)
    starter_cols = st.columns(3)
    starters = [
        "Find two consecutive integers whose product is 306",
        "Prove that √2 is irrational",
        "The sum of first n terms of an AP is 3n² + 4n. Find the AP.",
    ]
    for col, s in zip(starter_cols, starters):
        with col:
            if st.button(f"💬 {s[:45]}...", use_container_width=True, key=f"starter_{s[:10]}"):
                st.session_state.messages.append({"role":"user","content":s,"input_type":"TEXT"})
                st.rerun()

# ── RENDER CHAT HISTORY ───────────────────────────────────
for msg in st.session_state.messages:
    avatar = "🧑‍🎓" if msg["role"] == "user" else "📐"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg["role"] == "user":
            itype = msg.get("input_type", "TEXT")
            st.markdown(itype_html(itype), unsafe_allow_html=True)
            st.markdown(msg["content"])
        else:
            render_katex(msg["content"])

# ── DISPATCH HELPER ───────────────────────────────────────
def _dispatch(user_msg: str, input_type: str, engine: MathMate, file_text: str = ""):
    """Add user message, call MathMate, update state."""
    st.session_state.messages.append({"role":"user","content":user_msg,"input_type":input_type})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(itype_html(input_type), unsafe_allow_html=True)
        st.markdown(user_msg)

    with st.chat_message("assistant", avatar="📐"):
        with st.spinner("MathMate is thinking..."):
            response, revealed = engine.chat(
                user_message=user_msg,
                chat_history=st.session_state.messages[:-1],
                current_chapter=st.session_state.current_chapter,
                hint_count=st.session_state.hint_count,
                insist_count=st.session_state.insist_count,
                input_type=input_type,
                file_text=file_text,
            )
        render_katex(response)

    st.session_state.messages.append({"role":"assistant","content":response})

    if revealed:
        st.session_state.hint_count   = 0
        st.session_state.insist_count = 0
    elif is_explicit_insist(user_msg):
        st.session_state.insist_count = min(st.session_state.insist_count + 1, 5)
    else:
        st.session_state.hint_count = min(st.session_state.hint_count + 1, 4)

    st.rerun()


# ── INPUT AREA ────────────────────────────────────────────
if not st.session_state.index_ready:
    st.info("📤 Upload the NCERT PDF in the sidebar first, then build the knowledge base.")
    st.chat_input("Upload NCERT PDF first...", disabled=True)
else:
    # Multimodal input tabs
    tab_text, tab_voice, tab_image, tab_file = st.tabs(["💬 Text", "🎙️ Voice", "📷 Image", "📄 Worksheet"])

    # ── TEXT TAB ─────────────────────────────────────────
    with tab_text:
        if prompt := st.chat_input("Ask a question or paste a problem from NCERT...", key="chat_text"):
            _dispatch(prompt, "TEXT", mm)

    # ── VOICE TAB ────────────────────────────────────────
    with tab_voice:
        st.markdown("<div style='font-size:12px;color:#94a3b8;margin-bottom:10px;'>Record your question. MathMate will transcribe and respond.</div>", unsafe_allow_html=True)
        audio = st.audio_input("Hold to record", key="audio_input")
        if audio and st.button("🎙️ Send Voice Question", use_container_width=True, key="send_voice"):
            with st.spinner("Transcribing with Whisper..."):
                transcript, ok = voice_to_text(audio.read(), filename=audio.name if hasattr(audio,"name") else "audio.wav")
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
        if ws_file and st.button("📄 Load Worksheet", use_container_width=True, key="send_file"):
            with st.spinner("Extracting worksheet text..."):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(ws_file.read()); tmp_path = tmp.name
                try:
                    doc = fitz.open(tmp_path)
                    file_text = "\n\n".join(p.get_text("text") for p in doc)
                    doc.close()
                finally:
                    os.unlink(tmp_path)
            msg = f"[Worksheet uploaded: {ws_file.name}]\n\n{file_text[:3000]}"
            _dispatch(msg, "FILE_PDF", mm, file_text=file_text[:6000])


