# 🎓 MathMate v4.0 — NCERT Class 10 AI Tutor

<div align="center">

![MathMate](https://img.shields.io/badge/MathMate-v4.0-2B4C7E?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9%2B-3F7D4F?style=for-the-badge&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Llama_3.3_70b-B54834?style=for-the-badge&logo=meta&logoColor=white)
![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-6B6558?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-60a5fa?style=for-the-badge)

**A warm, subject-grounded AI tutor for CBSE Class 10 NCERT Mathematics & Science.**
*Built with a notebook-and-chalkboard aesthetic — designed for real Indian classrooms.*

</div>

---

## ✨ What is MathMate?

MathMate is a Retrieval-Augmented Generation (RAG) tutor that uses your own NCERT textbook PDF as its knowledge base. It supports **two distinct tutoring modes**, **four input types**, and **two subjects** — all in a beautifully designed paper-and-pencil notebook UI.

Unlike generic AI chatbots, MathMate is grounded in the CBSE curriculum. It cites chapter and page context from your uploaded textbook and refuses to invent facts.

---

## 🗂️ Project Structure

```
phaze1 rag/
├── app.py              # Streamlit UI — Paper & Chalkboard design, all input modes
├── mathmate.py         # Core RAG engine — dual-mode prompts, FAISS retrieval, LLM
├── build_index.py      # PDF ingestion + FAISS index builder (CLI + programmatic)
├── multimodal.py       # Voice (Whisper), Image (Vision LLM), PDF extraction
├── requirements.txt    # Pinned Python dependencies
├── run.bat             # One-click launcher for Windows
├── .env                # API keys (not committed)
├── faiss_index/
│   ├── math/           # FAISS index for Mathematics (index.faiss + index.pkl)
│   └── science/        # FAISS index for Science (index.faiss + index.pkl)
└── ncertbook-pdf/      # Place your NCERT PDFs here (not committed)
```

---

## 🚀 Features

### 🎯 Two Tutoring Modes
| Mode | Behaviour |
|------|-----------|
| **🧑‍🏫 TEACH** | Socratic method — never gives the answer directly. Guides you step by step with ORIENT → PROBE → UNSTICK → VERIFY → CELEBRATE. Switch to DIRECT from the sidebar anytime. |
| **⚡ DIRECT** | Full worked solution immediately — every step shown with the reason for each, verified by substitution, and boxed final answer. |

### 📚 Two Subjects (Lazy-Loaded)
- **🧮 Mathematics** — NCERT Class 10 Maths (Algebra, Geometry, Trigonometry, Statistics, etc.)
- **🔬 Science** — NCERT Class 10 Science (Physics + Chemistry in a single textbook)

Each subject's FAISS index is loaded into memory **only when that subject is selected** — saving RAM and startup time.

### 🎤 Four Input Types
| Tab | Method | Description |
|-----|--------|-------------|
| 💬 Text | Typed | Standard text question |
| 🎙️ Voice | Whisper STT | Speak your question; it's transcribed automatically |
| 📷 Image | Vision LLM | Photo of handwritten working or a textbook page |
| 📄 Document | PDF extract | Upload a worksheet; questions are extracted and listed |

### 🏫 Notebook & Chalkboard UI
- **Light mode**: Warm paper background (`#FAF7F0`), red notebook margin line, horizontal page ruling
- **Dark mode**: Chalkboard feel (`#1C2320` slate + `#EDE7D9` chalk white)
- **Fonts**: Lora (textbook serif) · IBM Plex Sans (UI) · IBM Plex Mono (equations/steps)
- **Motion**: Ink-reveal animation for new TEACH steps; border-draw animation for DIRECT boxed answers
- Fully respects `prefers-reduced-motion`

### 🔢 LaTeX Rendering
- Native Streamlit KaTeX — renders `$inline$` and `$$block$$` math natively
- `normalize_latex_delimiters()` converts `\[...\]` and `\(...\)` to `$...$` automatically
- `repair_malformed_latex()` fixes `\left$...\right$` malformations from the LLM

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **UI** | Streamlit 1.45 with custom CSS (Paper & Chalkboard design system) |
| **LLM** | `llama-3.3-70b-versatile` via **Groq** (ultra-fast inference) |
| **Embeddings** | `BAAI/bge-large-en-v1.5` via HuggingFace Sentence Transformers |
| **Vector Store** | FAISS (per-subject, lazy-loaded) |
| **PDF Extraction** | PyMuPDF (`fitz`) + per-page chapter detection |
| **Voice (STT)** | OpenAI Whisper via Groq API |
| **Vision** | Groq Vision LLM for handwriting / textbook page OCR |
| **Framework** | LangChain 0.3 (LCEL-compatible) |

---

## ⚡ Quick Start

### 1. Prerequisites

- Python 3.9+
- A free [Groq API Key](https://console.groq.com/keys) (takes 30 seconds to create)

### 2. Clone & Install

```bash
git clone https://github.com/Avvud/MathMate-.git
cd MathMate-

# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac / Linux

# Install dependencies
pip install -r requirements.txt
```

> **Note:** `faiss-gpu` is listed in `requirements.txt`. If you don't have a CUDA GPU, replace it with `faiss-cpu` before installing:
> ```bash
> pip install faiss-cpu
> ```

### 3. Configure API Key

Create a `.env` file in the project root:

```env
GROQ_API_KEY=gsk_your_key_here
```

Optionally override the model:

```env
GROQ_MODEL=llama-3.3-70b-versatile
```

### 4. Build the Knowledge Base

**Option A — via the app (recommended):**
1. Run the app (Step 5 below)
2. In the sidebar under **Upload Mathematics/Science PDF**, drop your NCERT PDF
3. Click **Build Knowledge Base** and wait ~1 minute

**Option B — via the CLI:**

```bash
# Mathematics
python build_index.py "ncertbook-pdf/math 10th.pdf" MATHEMATICS

# Science (Physics + Chemistry)
python build_index.py "ncertbook-pdf/science 10th.pdf" SCIENCE
```

Download the official free PDFs from [ncert.nic.in/textbook.php](https://ncert.nic.in/textbook.php) → Class X → Mathematics / Science.

### 5. Run the App

```bash
streamlit run app.py

# OR on Windows, double-click:
run.bat
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 🧠 How the RAG Pipeline Works

```
User Question
      │
      ▼
┌─────────────────┐
│ Embed question  │  (BAAI/bge-large-en-v1.5)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│ FAISS similarity search         │  (top-6 chunks, re-ranked by chapter)
│ Subject index: math / science   │
└────────┬────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────┐
│ Build system prompt                                  │
│  BASE_ROLE + TEACH_MODE_PROMPT or DIRECT_MODE_PROMPT │
│  + retrieved_chunks + input_type                     │
└────────┬─────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ ChatGroq (llama-3.3-70b)    │  max_tokens=2048, temperature=0.4
└────────┬────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│ normalize_latex_delimiters() + repair_malformed_latex│
│ render_response() → st.markdown (native KaTeX)      │
└─────────────────────────────────────────────────────┘
```

Per-session retrieval cache (`(question, chapter, subject) → chunks`) prevents redundant embedding lookups within a session.

---

## 📂 Building Indices (CLI Reference)

```bash
# Usage
python build_index.py <pdf_path> [MATHEMATICS|SCIENCE]

# Examples
python build_index.py "ncertbook-pdf/math 10th.pdf" MATHEMATICS
python build_index.py "ncertbook-pdf/science 10th.pdf" SCIENCE

# Output
faiss_index/
├── math/
│   ├── index.faiss
│   └── index.pkl
└── science/
    ├── index.faiss
    └── index.pkl
```

---

## 🔧 Configuration Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | *(required)* | Your Groq API key |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | LLM model to use |

---

## 🐛 Known Issues & Fixes

| Issue | Root Cause | Fix Applied |
|-------|-----------|-------------|
| Blank AI responses | `openai/gpt-oss-120b` reasoning model exhausts token budget silently | Default changed to `llama-3.3-70b-versatile`; empty-response guard added |
| LaTeX shows as raw text | Model uses `\[...\]` or `\(...\)` not recognised by KaTeX | `normalize_latex_delimiters()` converts them on the fly |
| `\left$...\right$` malformation | Known Llama generation quirk | `repair_malformed_latex()` converts to `\left(...\right)` |
| faiss ImportError | `faiss-gpu` not installed | Replace with `pip install faiss-cpu` if no CUDA GPU |

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Commit your changes: `git commit -m 'feat: add my feature'`
4. Push and open a PR

---

## 📄 License

MIT — free to use for educational purposes.

---

<div align="center">
Made with ❤️ for CBSE Class 10 students · Powered by Groq · Built on LangChain
</div>
