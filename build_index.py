"""
build_index.py — PDF Ingestion & FAISS Index Builder for MathMate v3.0
Supports per-subject indices: MATHEMATICS, PHYSICS, CHEMISTRY.
Each subject's index is stored in its own subdirectory under faiss_index/.
"""

import os
import re
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

FAISS_BASE_PATH = "faiss_index"
EMBEDDINGS_MODEL = "BAAI/bge-large-en-v1.5"

# Subject key → subdirectory name
SUBJECT_DIRS = {
    "MATHEMATICS": "math",
    "SCIENCE":     "science",
}

# Generic pattern: matches "Chapter 3", "Unit 2", "Section 5", etc.
CHAPTER_PATTERN = re.compile(
    r"(chapter|unit|section|part|module|lesson)\s*(\d{1,2})[^\w]*(.*?)\n",
    re.IGNORECASE,
)

# Legacy alias so old code importing FAISS_PATH still works
FAISS_PATH = os.path.join(FAISS_BASE_PATH, "math")


def get_faiss_path(subject: str = "MATHEMATICS") -> str:
    """Return the FAISS index directory for the given subject."""
    sub = SUBJECT_DIRS.get(subject.upper(), "math")
    return os.path.join(FAISS_BASE_PATH, sub)


def detect_chapter(text: str) -> tuple[str, str]:
    """
    Try to detect a chapter/unit/section heading in the first 400 chars of a page.
    Returns (chapter_id, chapter_name) e.g. ("Chapter 3", "Polynomials")
    or ("General", "General") if nothing found.
    """
    m = CHAPTER_PATTERN.search(text[:400])
    if m:
        prefix  = m.group(1).capitalize()
        num     = m.group(2)
        title   = m.group(3).strip().rstrip(":-").strip()
        ch_id   = f"{prefix} {num}"
        ch_name = f"{ch_id} — {title}" if title else ch_id
        return ch_id, ch_name
    return "General", "General"


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text page-by-page from a PDF.
    Returns list of {page_num, text, chapter_num, chapter_name} dicts.
    """
    pages = []
    doc = fitz.open(pdf_path)
    current_chapter_id   = "General"
    current_chapter_name = "General"

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")

        ch_id, ch_name = detect_chapter(text)
        if ch_id != "General":
            current_chapter_id   = ch_id
            current_chapter_name = ch_name

        pages.append({
            "page_num":    page_num,
            "text":        text,
            "chapter_num": current_chapter_id,
            "chapter_name": current_chapter_name,
        })

    doc.close()
    return pages


def clean_text(text: str) -> str:
    """Basic text cleaning."""
    text = text.replace("\r", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return text.strip()


def build_faiss_from_pdf(
    pdf_path: str,
    progress_callback=None,
    subject: str = "MATHEMATICS",
) -> bool:
    """
    Main entry point: reads a PDF, splits into chunks, builds & saves FAISS index
    for the given subject.
    progress_callback(step: str, pct: float) — optional for Streamlit progress bar.
    Returns True on success.
    """
    faiss_path = get_faiss_path(subject)

    if progress_callback:
        progress_callback("📖 Reading PDF pages...", 0.05)

    pages = extract_text_from_pdf(pdf_path)
    total_pages = len(pages)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    docs: list[Document] = []

    for i, page in enumerate(pages):
        if progress_callback and i % 10 == 0:
            pct = 0.05 + 0.35 * (i / total_pages)
            progress_callback(f"✂️ Splitting page {i+1}/{total_pages}...", pct)

        cleaned = clean_text(page["text"])
        if len(cleaned) < 50:
            continue

        chunks = splitter.split_text(cleaned)
        for chunk in chunks:
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "page":         page["page_num"],
                    "chapter_num":  page["chapter_num"],
                    "chapter_name": page["chapter_name"],
                    "source":       os.path.basename(pdf_path),
                    "subject":      subject,
                },
            ))

    if not docs:
        raise ValueError("No text could be extracted from the PDF.")

    if progress_callback:
        progress_callback(f"🧠 Building embeddings for {len(docs)} chunks...", 0.45)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

    if progress_callback:
        progress_callback("💾 Creating FAISS index...", 0.85)

    store = FAISS.from_documents(docs, embeddings)
    os.makedirs(faiss_path, exist_ok=True)
    store.save_local(faiss_path)

    if progress_callback:
        progress_callback("✅ Index ready!", 1.0)

    return True


def is_index_built(subject: str = "MATHEMATICS") -> bool:
    """Check if a FAISS index already exists for the given subject."""
    return os.path.exists(os.path.join(get_faiss_path(subject), "index.faiss"))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python build_index.py <path_to_pdf> [MATHEMATICS|SCIENCE]")
        sys.exit(1)

    pdf  = sys.argv[1]
    subj = sys.argv[2].upper() if len(sys.argv) > 2 else "MATHEMATICS"

    if not os.path.exists(pdf):
        print(f"File not found: {pdf}")
        sys.exit(1)

    def cli_progress(step, pct):
        bar = "█" * int(pct * 20)
        print(f"\r[{bar:<20}] {int(pct*100)}%  {step}", end="", flush=True)

    build_faiss_from_pdf(pdf, progress_callback=cli_progress, subject=subj)
    print(f"\n\n✅ FAISS index saved to ./{get_faiss_path(subj)}/")
