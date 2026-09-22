"""
mathmate.py — MathMate v4.0 Core RAG Engine
Two-mode: TEACH (Socratic) / DIRECT (full solution)
Multi-subject: MATHEMATICS · PHYSICS · CHEMISTRY
"""

import os
import re
import time
from dotenv import load_dotenv

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from groq import RateLimitError

from build_index import get_faiss_path, EMBEDDINGS_MODEL

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# ──────────────────────────────────────────────────────────
#  PROMPT TEMPLATES — shared base + two mode‑specific tails
#  Uses str.format() — all LaTeX { } must be escaped as {{ }}
# ──────────────────────────────────────────────────────────

BASE_ROLE = """\
You are MathMate, a Class 10 NCERT Mathematics assistant (CBSE curriculum).
You always write math in LaTeX: inline $...$, block $$...$$. Never write
plain-text math like "x^2+5x" or "sqrt(144)".
Use ONLY the retrieved NCERT context below for formulas/theorems/facts.
If the context doesn't cover the question, say so instead of inventing a fact.
Never mention pipeline internals (Whisper, base64, PyMuPDF, FAISS, embeddings).

## RETRIEVED CONTEXT
{retrieved_chunks}

## INPUT TYPE THIS TURN: {input_type}
TEXT — standard typed message, treat normally.
VOICE_TRANSCRIPT — informal/spoken phrasing from Whisper; silently convert
  spoken math to LaTeX before responding (e.g. "root of 144" -> $\\sqrt{{144}}$).
  Never mention it was transcribed.
IMAGE_HANDWRITTEN — the description below is the student's own handwritten
  working, already extracted by a vision model. Treat it as their attempt,
  not as a question to answer fresh. Reference specific lines/steps.
IMAGE_TEXTBOOK — description is an NCERT question/page extracted by a
  vision model. Cross-reference with retrieved context.
FILE_PDF — a worksheet/question paper was extracted. List every question
  found (do not truncate or drop any) and ask which one to tackle first;
  never solve all of them unprompted.
"""

TEACH_MODE_PROMPT = BASE_ROLE + """
## MODE: TEACH — Socratic guidance only

Never state the final answer, under any circumstances, in this mode — even
if the student insists, begs, or claims a deadline. If they explicitly ask
for the answer, warmly acknowledge the request and tell them they can switch
to "Just solve it" mode in the sidebar if they want the full solution — do
not give in and solve it yourself here.

Pick exactly ONE response mode per turn:
- ORIENT: student doesn't know where to start. Ask what concept/theorem the
  problem resembles; ask them to list what's given vs. unknown.
- PROBE: student has attempted something (text or image). Name what's
  correct first, specifically. If something's wrong, ask a question that
  exposes the gap — never just say "wrong" and never give the fix directly.
- UNSTICK: student is stuck mid-solution. Give the smallest possible nudge:
  a formula name, one variable, or one targeted question. Never restate the
  whole problem or complete a step for them.
- VERIFY: student claims an answer. Don't confirm or deny it — ask them to
  check it by substitution or an alternate method.
- CELEBRATE: student shows genuine understanding. Praise the specific
  reasoning, connect it to a real-world example, offer a related challenge
  as optional.

Rules:
- Show at most ONE step at a time, only after they've attempted the
  previous one.
- Every response ends with exactly one question that moves them forward.
- Keep responses 4-8 lines unless walking through a single step in detail.
- Warm and patient, never condescending. Use "we"/"let's" occasionally.
"""

DIRECT_MODE_PROMPT = BASE_ROLE + """
## MODE: DIRECT — complete solution

Give the full worked solution immediately and completely:
- Show every step in order with a brief reason for each (which rule/formula
  is being applied and why).
- State the final answer clearly, on its own line, labeled "Answer:".
- Verify the answer yourself within the response (substitution or an
  alternate method) and show that check explicitly.
- Do not withhold any step. Do not end with a Socratic question — instead,
  end with one short line offering to explain any specific step further if
  the student wants it expanded.
"""


def build_system_prompt(mode: str, **kwargs) -> str:
    """Build the system prompt for the given mode with filled‑in context."""
    template = TEACH_MODE_PROMPT if mode == "TEACH" else DIRECT_MODE_PROMPT
    return template.format(**kwargs)


# ──────────────────────────────────────────────────────────
#  SUBJECT METADATA
# ──────────────────────────────────────────────────────────

SUBJECTS = {
    "MATHEMATICS": {
        "label": "🧮 Mathematics",
        "color": "#6ee7b7",
        "avatar": "🧮",
        "description": "NCERT Class 10 · Socratic Method",
    },
    "SCIENCE": {
        "label": "🔬 Science",
        "color": "#60a5fa",
        "avatar": "🔬",
        "description": "NCERT Class 10 · Physics + Chemistry",
    },
}

# ──────────────────────────────────────────────────────────
#  HELPERS
# ──────────────────────────────────────────────────────────


def build_messages(
    system_prompt: str, chat_history: list[dict], user_message: str
) -> list:
    """
    Build a real per‑turn LangChain message list instead of
    flattening chat history into a single string.
    """
    messages = [SystemMessage(content=system_prompt)]
    for m in chat_history[-8:]:
        cls = HumanMessage if m["role"] == "user" else AIMessage
        messages.append(cls(content=m["content"]))
    messages.append(HumanMessage(content=user_message))
    return messages


def clean_retrieved(docs) -> str:
    if not docs:
        return "No specific context found for this question."
    parts = []
    for doc in docs:
        ch = doc.metadata.get("chapter_name", "")
        pg = doc.metadata.get("page", "")
        header = f"[{ch}, p.{pg}]" if ch else ""
        parts.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(parts)


# ──────────────────────────────────────────────────────────
#  MATHMATE ENGINE
# ──────────────────────────────────────────────────────────


class MathMate:
    def __init__(self):
        self._stores: dict[str, FAISS | None] = {
            "MATHEMATICS": None,
            "SCIENCE":     None,
        }
        self._llm: ChatGroq | None = None
        self._embeddings: HuggingFaceEmbeddings | None = None
        # Per‑session retrieval cache: (question, chapter, subject) → chunks str
        self._retrieve_cache: dict[tuple[str, str, str], str] = {}
        self._load()

    def _load(self):
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY is not set in .env")

        self._llm = ChatGroq(
            api_key=api_key,
            model=MODEL,
            temperature=0.4,
        )

        self._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

        # Indices are NOT loaded eagerly — they are lazy-loaded on first
        # use via _ensure_index_loaded() to save memory and startup time.

    def _ensure_index_loaded(self, subject: str) -> bool:
        """
        Lazy-load the FAISS index for the given subject only when needed.
        Returns True if the index is (now) loaded, False if no index exists.
        """
        subject = subject.upper()
        if self._stores.get(subject) is not None:
            return True  # Already loaded

        path = get_faiss_path(subject)
        index_file = os.path.join(path, "index.faiss")
        if not os.path.exists(index_file):
            return False  # No index built yet

        # Safe: the index is built locally from the user's own uploaded
        # PDF, never loaded from an untrusted remote source.
        self._stores[subject] = FAISS.load_local(
            path,
            self._embeddings,
            allow_dangerous_deserialization=True,
        )
        return True

    def reload_index(self, subject: str = "MATHEMATICS"):
        """Reload the FAISS index for a specific subject after building."""
        subject = subject.upper()
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)
        # Force re-load by clearing cached store first
        self._stores[subject] = None
        self._ensure_index_loaded(subject)

    def _retrieve(self, question: str, chapter: str, subject: str, k: int = 4) -> str:
        subject = subject.upper()
        cache_key = (question, chapter, subject)
        if cache_key in self._retrieve_cache:
            return self._retrieve_cache[cache_key]

        # Lazy-load: only load this subject's index when first needed
        self._ensure_index_loaded(subject)

        store = self._stores.get(subject)
        if store is None:
            result = f"No knowledge base loaded for {subject}. Please upload the textbook PDF first."
            self._retrieve_cache[cache_key] = result
            return result

        retriever = store.as_retriever(search_kwargs={"k": k + 2})
        docs = retriever.invoke(question)

        chapter_lower = chapter.lower()
        preferred = [d for d in docs if chapter_lower in d.metadata.get("chapter_name", "").lower()]
        fallback  = [d for d in docs if d not in preferred]

        result = clean_retrieved((preferred + fallback)[:k])
        self._retrieve_cache[cache_key] = result
        return result

    def _call_llm(self, messages: list, max_retries: int = 3) -> str:
        """
        Invoke the LLM with a full message list.
        Handles rate‑limiting (with proper exception type) and context‑length
        errors gracefully.
        """
        last_error = "Unknown error"
        for attempt in range(max_retries):
            try:
                return self._llm.invoke(messages).content
            except RateLimitError:
                wait = 5 + attempt * 3
                time.sleep(wait)
                continue
            except Exception as e:
                err = str(e)
                last_error = err
                if "context_length" in err.lower() or "too many tokens" in err.lower():
                    # Prompt too long — trim to system + latest user only
                    if len(messages) > 2:
                        messages = [messages[0], messages[-1]]
                        continue
                    return (
                        "⚠️ Your conversation is too long for the model context. "
                        "Please click **🔄 New Problem** or **🗑️ Clear Chat** to start fresh."
                    )
                # For all other errors, break immediately — no point retrying
                break
        return (
            f"⚠️ Could not reach the AI. **Reason:** `{last_error[:200]}`\n\n"
            "Please check your internet connection or Groq API key and try again."
        )

    def chat(
        self,
        user_message: str,
        chat_history: list[dict],
        mode: str = "TEACH",
        current_chapter: str = "General",
        input_type: str = "TEXT",
        file_text: str = "",
        subject: str = "MATHEMATICS",
    ) -> str:
        """
        Main chat method. Returns a plain response string.
        mode is "TEACH" (Socratic) or "DIRECT" (full solution).
        """
        subject = subject.upper()

        retrieved = self._retrieve(user_message, current_chapter, subject)

        system = build_system_prompt(
            mode,
            retrieved_chunks=retrieved,
            input_type=input_type,
        )

        messages = build_messages(system, chat_history, user_message)

        response = self._call_llm(messages)
        return response.strip()

    @property
    def index_loaded(self) -> dict[str, bool]:
        """Check which subjects have an index on disk (without loading them)."""
        return {
            subj: os.path.exists(os.path.join(get_faiss_path(subj), "index.faiss"))
            for subj in self._stores
        }
